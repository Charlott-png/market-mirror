"""MM-022 contracts written before drag-and-drop implementation."""

from io import BytesIO
from pathlib import Path
import re

import pytest
from sqlalchemy import func, select

from tests.test_marketplace import listing_data, sign_in
from tests.test_seller_profile import Page


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def dropzone_web(db_app):
    db_app.config.update(WTF_CSRF_ENABLED=False,
                         SECRET_KEY="isolated-image-dropzone-secret")
    return db_app.test_client()


def create_page(client, user):
    sign_in(client, user)
    return Page(client.get("/listings/new"))


def any_status_page(response):
    """Reuse the project parser for expected form-validation 400 responses."""
    original = response.status_code
    response.status_code = 200
    try:
        return Page(response)
    finally:
        response.status_code = original


def image_input(page):
    return page.one("input", id="image", name="image", type="file")


def test_new_listing_has_accessible_multi_image_dropzone(dropzone_web, user_factory):
    page = create_page(dropzone_web, user_factory())
    zone = page.one("div", id="product-image-dropzone", **{
        "class": "image-dropzone", "data-max-bytes": "5242880",
    })
    assert "five" in zone["text"].lower()
    assert "5 MiB" in zone["text"] and "25 MiB" in zone["text"]
    control = image_input(page)
    assert control["attrs"]["accept"] == "image/jpeg,image/png"
    assert "multiple" in control["attrs"]
    assert control["attrs"]["aria-describedby"].split() == [
        "product-image-drop-instruction", "product-image-help",
        "product-image-upload-status", "image-errors",
    ]
    label = page.one("label", **{"for": "image"})
    assert "Optional product photos" in label["text"]


def test_security_policy_allows_local_blob_thumbnail(dropzone_web, user_factory):
    """The browser preview uses a temporary local ``blob:`` image URL."""
    sign_in(dropzone_web, user_factory())
    response = dropzone_web.get("/listings/new")
    policy = response.headers["Content-Security-Policy"]
    assert re.search(r"(?:^|;)\s*img-src\s+[^;]*\bblob:", policy)


def test_preview_and_feedback_begin_empty_and_safe(dropzone_web, user_factory):
    page = create_page(dropzone_web, user_factory())
    status = page.one("p", id="product-image-upload-status", **{
        "class": "image-upload-status", "aria-live": "polite",
    })
    assert not status["text"].strip()
    preview = page.one(id="product-image-preview-list", **{
        "class": "image-upload-preview-list",
    })
    assert "hidden" in preview["attrs"]
    page.one("div", id="image-errors", role="alert")
    assert not any(name.lower().startswith("on")
                   for node in page.nodes for name in node["attrs"])


def test_invalid_new_listing_rerenders_dropzone_without_creating_data(
        dropzone_web, user_factory, db_session):
    from app.models import Product

    sign_in(dropzone_web, user_factory())
    response = dropzone_web.post("/listings/new", data=listing_data(title="x"))
    assert response.status_code == 400
    page = any_status_page(response)
    page.one(id="product-image-dropzone")
    image_input(page)
    assert db_session.scalar(select(func.count()).select_from(Product)) == 0


def test_edit_listing_receives_replacement_dropzone_without_vision_ui(
        dropzone_web, user_factory, product_factory):
    owner = user_factory()
    product = product_factory(seller=owner)
    sign_in(dropzone_web, owner)
    for response in (
        dropzone_web.get(f"/listings/{product.id}/edit"),
        dropzone_web.post(f"/listings/{product.id}/edit",
                          data=listing_data(title="x", version=product.version)),
    ):
        assert response.status_code in {200, 400}
        page = any_status_page(response)
        image_input(page)
        page.one(id="product-image-dropzone")
        page.one(id="product-image-preview-list")
        assert not page.find(id="vision-ai-enabled")


@pytest.mark.parametrize("path", ["/auth/login", "/auth/register", "/account/profile"])
def test_other_generic_forms_do_not_receive_dropzone(
        dropzone_web, user_factory, path):
    if path == "/account/profile":
        sign_in(dropzone_web, user_factory())
    page = Page(dropzone_web.get(path))
    assert not page.find(id="product-image-dropzone")


def test_anonymous_route_stays_protected_and_read_only(dropzone_web, db_session):
    from app.models import Product, User

    before = tuple(db_session.scalar(select(func.count()).select_from(model))
                   for model in (User, Product))
    response = dropzone_web.get("/listings/new")
    assert response.status_code == 302
    assert response.location.endswith("/auth/login?next=%2Flistings%2Fnew")
    assert tuple(db_session.scalar(select(func.count()).select_from(model))
                 for model in (User, Product)) == before


def test_rendering_dropzone_does_not_write_database_or_uploads(
        dropzone_web, user_factory, db_session, db_app):
    from app.extensions import db

    upload_root = Path(db_app.config["UPLOAD_FOLDER"])
    before = {table.name: db_session.execute(select(table)).all()
              for table in db.metadata.sorted_tables}
    create_page(dropzone_web, user_factory())
    # The user creation is intentional fixture setup, so snapshot after it and
    # make a second render the mutation check.
    before = {table.name: db_session.execute(select(table)).all()
              for table in db.metadata.sorted_tables}
    assert dropzone_web.get("/listings/new").status_code == 200
    after = {table.name: db_session.execute(select(table)).all()
             for table in db.metadata.sorted_tables}
    assert after == before
    assert not upload_root.exists() or not list(upload_root.iterdir())


def mm022_script():
    source = (PROJECT_ROOT / "app/static/js/market.js").read_text(encoding="utf-8")
    match = re.search(r"// MM-022:start(?P<body>.*?)// MM-022:end", source, re.S)
    assert match, "The guarded MM-022 script block is missing"
    return source, match.group("body")


def test_javascript_has_guarded_common_picker_and_drop_path():
    source, block = mm022_script()
    for token in (
        "product-image-dropzone", "product-image-preview-list",
        "product-image-upload-status", "MAX_IMAGE_COUNT", "MAX_TOTAL_IMAGE_BYTES",
        "const useFiles", "DataTransfer", "URL.createObjectURL",
        "URL.revokeObjectURL", "textContent", "pagehide",
        "image/jpeg", "image/png", "5 * 1024 * 1024",
    ):
        assert token in block
    for event in ("change", "dragenter", "dragover", "dragleave", "drop", "dragend"):
        assert re.search(rf"addEventListener\(['\"]{event}['\"]", block)
    assert block.count("useFiles(") >= 2  # picker call and drop call
    assert "data.delete('image')" in source or 'data.delete("image")' in source


def test_javascript_rejects_ambiguity_and_cleans_every_state():
    _, block = mm022_script()
    assert re.search(r"selected\.length\s*>\s*MAX_IMAGE_COUNT", block)
    assert "webkitGetAsEntry" in block
    assert re.search(r"dragDepth\s*\+=\s*1", block)
    assert re.search(r"Math\.max\(0,\s*dragDepth\s*-\s*1\)", block)
    assert "is-drag-over" in block
    assert "dropEffect" in block and "copy" in block
    assert re.search(r"input\.files\s*=", block)
    assert re.search(r"input\.value\s*=\s*['\"]['\"]", block)
    assert "currentObjectUrls" in block and "replaceChildren" in block


def test_preview_script_cannot_upload_or_submit_automatically():
    _, block = mm022_script()
    lowered = block.lower()
    assert "fetch(" not in lowered
    assert "xmlhttprequest" not in lowered
    assert ".submit(" not in lowered
    assert "requestsubmit(" not in lowered
    assert "/ai/" not in lowered and "/media/" not in lowered


def css_rule(css, selector):
    matches = re.findall(rf"{re.escape(selector)}\s*\{{([^}}]*)\}}", css, re.S)
    assert matches, f"Missing CSS rule for {selector}"
    return "\n".join(matches)


def test_css_has_idle_drag_focus_and_bounded_preview_states():
    css = (PROJECT_ROOT / "app/static/css/style.css").read_text(encoding="utf-8")
    idle = css_rule(css, ".image-dropzone")
    drag = css_rule(css, ".image-dropzone.is-drag-over")
    focus = css_rule(css, ".image-dropzone:focus-within")
    image = css_rule(css, ".image-upload-preview-item img")
    filename = css_rule(css, ".image-upload-preview-name")
    assert "dashed" in idle and "min-width: 0" in idle
    assert "solid" in drag and ("box-shadow" in drag or "outline" in drag)
    assert "outline" in focus
    assert "max-width: 100%" in image and "object-fit:" in image
    assert "overflow-wrap:" in filename and "min-width: 0" in filename
    assert ".image-upload-preview-list[hidden]" in css


def test_existing_server_accepts_valid_image_and_normalizes_it(
        dropzone_web, user_factory, db_session, db_app):
    from PIL import Image
    from app.models import Product

    stream = BytesIO()
    Image.new("RGBA", (80, 40), (20, 100, 140, 128)).save(stream, format="PNG")
    stream.seek(0)
    sign_in(dropzone_web, user_factory())
    response = dropzone_web.post("/listings/new", data=listing_data(
        request_token="mm022-valid", image=(stream, "<b>photo</b>.PNG")),
        content_type="multipart/form-data")
    assert response.status_code == 302
    product = db_session.scalar(select(Product))
    stored = Path(db_app.config["UPLOAD_FOLDER"]) / product.image_filename
    assert stored.is_file() and product.image_filename.endswith(".jpg")
    with Image.open(stored) as image:
        assert image.format == "JPEG" and image.size == (80, 40)


@pytest.mark.parametrize(("payload", "filename"), [
    (b"", "empty.png"),
    (b"<script>not an image</script>", "spoof.png"),
    (b"x" * (5 * 1024 * 1024 + 1), "too-large.jpg"),
], ids=["empty", "spoofed", "over-five-mib"])
def test_existing_server_rejects_bad_images_without_rows_or_orphans(
        dropzone_web, user_factory, db_session, db_app, payload, filename):
    from app.models import Product

    sign_in(dropzone_web, user_factory())
    response = dropzone_web.post("/listings/new", data=listing_data(
        request_token="mm022-invalid", image=(BytesIO(payload), filename)),
        content_type="multipart/form-data")
    assert response.status_code == 400
    assert db_session.scalar(select(func.count()).select_from(Product)) == 0
    upload_root = Path(db_app.config["UPLOAD_FOLDER"])
    assert not upload_root.exists() or not list(upload_root.iterdir())

