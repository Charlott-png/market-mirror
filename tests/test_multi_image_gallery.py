"""MM-026 multi-image contracts, written before implementation."""

from decimal import Decimal
from io import BytesIO
from pathlib import Path
import re
from uuid import uuid4

from PIL import Image
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from tests.test_marketplace import listing_data, sign_in


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def gallery_web(db_app):
    db_app.config.update(WTF_CSRF_ENABLED=False,
                         SECRET_KEY="isolated-mm026-gallery-secret")
    return db_app.test_client()


def product_image_model():
    from app import models
    assert hasattr(models, "ProductImage"), "MM-026 ProductImage model is missing"
    return models.ProductImage


def picture(name, color="teal", fmt="PNG", size=(80, 60)):
    stream = BytesIO()
    Image.new("RGB", size, color).save(stream, format=fmt)
    stream.seek(0)
    return stream, name


def stored_picture(app, color="teal"):
    root = Path(app.config["UPLOAD_FOLDER"])
    root.mkdir(parents=True, exist_ok=True)
    name = uuid4().hex + ".jpg"
    Image.new("RGB", (100, 70), color).save(root / name, format="JPEG")
    return name


def test_product_image_model_orders_slots_and_rejects_duplicates(
        db_app, product_factory, db_session):
    ProductImage = product_image_model()
    product = product_factory()
    names = [uuid4().hex + ".jpg" for _ in range(2)]
    db_session.add_all([
        ProductImage(product_id=product.id, filename=names[1], position=1),
        ProductImage(product_id=product.id, filename=names[0], position=0),
    ])
    db_session.commit()
    db_session.expire_all()
    stored = db_session.get(type(product), product.id)
    assert [row.position for row in stored.gallery_images] == [0, 1]
    assert stored.gallery_images[0].created_at.tzinfo is not None

    db_session.add(ProductImage(product_id=product.id,
                                filename=uuid4().hex + ".jpg", position=1))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


@pytest.mark.parametrize("position", [-1, 5])
def test_product_image_rejects_invalid_positions(db_app, product_factory,
                                                 db_session, position):
    ProductImage = product_image_model()
    product = product_factory()
    with pytest.raises((ValueError, IntegrityError)):
        db_session.add(ProductImage(product_id=product.id,
            filename=uuid4().hex + ".jpg", position=position))
        db_session.commit()
    db_session.rollback()


def test_create_listing_with_three_images_sets_cover_rows_and_files(
        gallery_web, db_app, user_factory, db_session):
    from app.models import Product
    ProductImage = product_image_model()
    seller = user_factory()
    sign_in(gallery_web, seller)
    images = [picture("front.png", "red"), picture("side.jpg", "green", "JPEG"),
              picture("back.png", "blue")]
    data = listing_data(title="Three angle laptop", request_token="mm026-three")
    data["image"] = images
    response = gallery_web.post("/listings/new", data=data,
                                content_type="multipart/form-data")
    assert response.status_code == 302
    product = db_session.scalar(select(Product))
    rows = db_session.scalars(select(ProductImage).order_by(ProductImage.position)).all()
    assert [row.position for row in rows] == [0, 1, 2]
    assert product.image_filename == rows[0].filename
    assert all((Path(db_app.config["UPLOAD_FOLDER"]) / row.filename).is_file()
               for row in rows)
    assert len({row.filename for row in rows}) == 3


def test_six_images_reject_without_rows_or_files(gallery_web, db_app,
                                                  user_factory, db_session):
    from app.models import Product
    ProductImage = product_image_model()
    sign_in(gallery_web, user_factory())
    data = listing_data(title="Too many angles", request_token="mm026-six")
    data["image"] = [picture(f"angle-{index}.png", color)
                     for index, color in enumerate(("red", "green", "blue", "black", "white", "yellow"))]
    response = gallery_web.post("/listings/new", data=data,
                                content_type="multipart/form-data")
    assert response.status_code == 400
    assert b"five" in response.data.lower()
    assert db_session.query(Product).count() == 0
    assert db_session.query(ProductImage).count() == 0
    root = Path(db_app.config["UPLOAD_FOLDER"])
    assert not root.exists() or not list(root.iterdir())


def test_bad_later_image_compensates_all_new_files(gallery_web, db_app,
                                                    user_factory, db_session):
    from app.models import Product
    ProductImage = product_image_model()
    sign_in(gallery_web, user_factory())
    data = listing_data(title="Atomic picture group", request_token="mm026-bad-later")
    data["image"] = [picture("good-one.png", "red"),
                     picture("good-two.png", "blue"),
                     (BytesIO(b"not a real image"), "bad-three.png")]
    response = gallery_web.post("/listings/new", data=data,
                                content_type="multipart/form-data")
    assert response.status_code == 400
    assert db_session.query(Product).count() == 0
    assert db_session.query(ProductImage).count() == 0
    root = Path(db_app.config["UPLOAD_FOLDER"])
    assert not root.exists() or not list(root.iterdir())


def test_edit_empty_keeps_gallery_and_new_group_replaces_atomically(
        gallery_web, db_app, user_factory, product_factory, db_session):
    ProductImage = product_image_model()
    owner = user_factory()
    old_names = [stored_picture(db_app, "red"), stored_picture(db_app, "blue")]
    product = product_factory(seller=owner, image_filename=old_names[0])
    db_session.add_all([ProductImage(product_id=product.id, filename=name, position=index)
                        for index, name in enumerate(old_names)])
    db_session.commit()
    sign_in(gallery_web, owner)

    keep = gallery_web.post(f"/listings/{product.id}/edit",
        data=listing_data(title=product.title, version=product.version,
                          request_token="unused-edit-token"))
    assert keep.status_code == 302
    assert [row.filename for row in product.gallery_images] == old_names
    assert all((Path(db_app.config["UPLOAD_FOLDER"]) / name).is_file() for name in old_names)

    db_session.refresh(product)
    replace = listing_data(title=product.title, version=product.version,
                           request_token="unused-edit-token-2")
    replace["image"] = [picture("new-cover.png", "green"),
                        picture("new-detail.png", "yellow")]
    response = gallery_web.post(f"/listings/{product.id}/edit", data=replace,
                                content_type="multipart/form-data")
    assert response.status_code == 302
    db_session.expire_all()
    current = db_session.get(type(product), product.id)
    new_names = [row.filename for row in current.gallery_images]
    assert len(new_names) == 2 and current.image_filename == new_names[0]
    assert not any((Path(db_app.config["UPLOAD_FOLDER"]) / name).exists()
                   for name in old_names)


def test_detail_renders_ordered_gallery_and_additional_media_permissions(
        gallery_web, db_app, user_factory, product_factory, db_session):
    ProductImage = product_image_model()
    owner, stranger = user_factory(), user_factory()
    names = [stored_picture(db_app, color) for color in ("red", "green", "blue")]
    product = product_factory(seller=owner, image_filename=names[0])
    db_session.add_all([ProductImage(product_id=product.id, filename=name, position=index)
                        for index, name in enumerate(names)])
    db_session.commit()

    html = gallery_web.get(f"/products/{product.id}").get_data(as_text=True)
    assert 'id="product-gallery-thumbnails"' in html
    assert html.count('class="product-gallery-thumbnail"') == 3
    assert html.index(names[0]) < html.index(names[1]) < html.index(names[2])
    assert gallery_web.get(f"/media/products/{names[2]}").status_code == 200

    product.status = "archived"
    db_session.commit()
    assert gallery_web.get(f"/media/products/{names[2]}").status_code == 404
    sign_in(gallery_web, stranger)
    assert gallery_web.get(f"/media/products/{names[2]}").status_code == 404
    sign_in(gallery_web, owner)
    assert gallery_web.get(f"/media/products/{names[2]}").status_code == 200


def test_one_image_and_legacy_cover_keep_simple_lightbox_without_strip(
        gallery_web, db_app, product_factory):
    ProductImage = product_image_model()
    first = stored_picture(db_app)
    gallery_product = product_factory(image_filename=first)
    from app.extensions import db
    db.session.add(ProductImage(product_id=gallery_product.id, filename=first, position=0))
    legacy = product_factory(image_filename=stored_picture(db_app, "navy"))
    db.session.commit()
    for product in (gallery_product, legacy):
        html = gallery_web.get(f"/products/{product.id}").get_data(as_text=True)
        assert 'id="product-image-trigger"' in html
        assert 'id="product-image-dialog"' in html
        assert 'id="product-gallery-thumbnails"' not in html


def test_gallery_static_contracts_cover_upload_ai_switching_and_css():
    dropzone = (PROJECT_ROOT / "app/templates/_image_dropzone.html").read_text(encoding="utf-8")
    product = (PROJECT_ROOT / "app/templates/product.html").read_text(encoding="utf-8")
    script = (PROJECT_ROOT / "app/static/js/market.js").read_text(encoding="utf-8")
    css = (PROJECT_ROOT / "app/static/css/style.css").read_text(encoding="utf-8")
    for token in ("multiple", "five", "25 MiB", "Cover photo", "product-image-preview-list"):
        assert token.lower() in dropzone.lower()
    for token in ("product-gallery-thumbnails", "product-gallery-thumbnail",
                  "aria-current", "product-gallery-status"):
        assert token in product
    for token in ("MAX_IMAGE_COUNT", "MAX_TOTAL_IMAGE_BYTES", "detail.files",
                  "currentObjectUrls", "product-gallery-thumbnail",
                  "Showing photo", "lightbox"):
        assert token in script
    assert "detail.file" in script and "cover photo" in script.lower()
    assert "data.delete('image')" in script
    for token in (".image-upload-preview-list", ".product-gallery-thumbnails",
                  ".product-gallery-thumbnail", "aria-current"):
        assert token in css
    assert "44px" in css and "overflow" in css


def test_maintenance_counts_gallery_as_referenced_and_reports_cover_drift(
        db_app, product_factory, db_session):
    ProductImage = product_image_model()
    root = Path(db_app.config["UPLOAD_FOLDER"])
    root.mkdir(parents=True, exist_ok=True)
    cover = stored_picture(db_app, "red")
    extra = stored_picture(db_app, "green")
    product = product_factory(image_filename=cover)
    db_session.add_all([ProductImage(product_id=product.id, filename=cover, position=0),
                        ProductImage(product_id=product.id, filename=extra, position=1)])
    db_session.commit()
    result = db_app.test_cli_runner().invoke(args=["maintenance", "images", "--delete-orphans"])
    assert result.exit_code == 0, result.output
    assert (root / cover).exists() and (root / extra).exists()
    assert "0 cover drift" in result.output.lower()

    product.image_filename = uuid4().hex + ".jpg"
    db_session.commit()
    result = db_app.test_cli_runner().invoke(args=["maintenance", "images"])
    assert "1 cover drift" in result.output.lower()

