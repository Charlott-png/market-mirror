"""Loopback-only MM-028 browser fixture; never reads the real database.

Run with: python -m tests.preview_recently_viewed
Stop with Ctrl+C. Temporary data remains under .pytest-tmp only.
"""

from decimal import Decimal
from pathlib import Path
import tempfile

from flask import jsonify, request
from PIL import Image
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import Product, RecentProductView, User


PASSWORD = "Recently viewed fixture passphrase!"


def build_preview():
    root = Path(__file__).resolve().parents[1] / ".pytest-tmp"
    root.mkdir(exist_ok=True)
    fixture_dir = Path(tempfile.mkdtemp(prefix="mm028-browser-", dir=root))
    uploads = fixture_dir / "uploads"
    uploads.mkdir()
    image_name = "8" * 32 + ".jpg"
    Image.new("RGB", (900, 600), "#426b76").save(uploads / image_name)
    application = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": True,
        "SQLALCHEMY_DATABASE_URI":
            f"sqlite:///{(fixture_dir / 'recently-viewed.sqlite').as_posix()}",
        "UPLOAD_FOLDER": str(uploads),
        "AI_FOLDER": str(fixture_dir / "ai"),
        "TEMPLATES_AUTO_RELOAD": True,
    })
    with application.app_context():
        db.create_all()
        password_hash = generate_password_hash(PASSWORD)
        shopper = User(username="recent-shopper",
                       email="shopper@recent-fixture.test",
                       password_hash=password_hash,
                       personalization=False)
        seller = User(username="recent-seller",
                      email="seller@recent-fixture.test",
                      password_hash=password_hash)
        db.session.add_all([shopper, seller])
        db.session.flush()
        products = [
            ("Fixture digital camera", "electronics", "good", "89.00"),
            ("Fixture compact camera", "electronics", "like_new", "59.00"),
            ("Fixture silver laptop", "electronics", "good", "310.00"),
            ("Fixture wireless mouse", "electronics", "new", "22.00"),
            ("Fixture desktop monitor", "electronics", "fair", "75.00"),
            ("Fixture adventure book", "books_media", "good", "12.00"),
        ]
        for title, category, condition, price in products:
            db.session.add(Product(
                seller_id=seller.id, title=title,
                description="Temporary MM-028 browser fixture product.",
                price=Decimal(price), currency="USD", category=category,
                condition=condition, status="active",
                image_filename=image_name))
        db.session.commit()
        shopper_id = shopper.id

    @application.get("/fixture-mm028-state")
    def fixture_state():
        rows = db.session.query(RecentProductView).filter_by(
            user_id=shopper_id).order_by(
                RecentProductView.viewed_at.desc(),
                RecentProductView.product_id.desc()).all()
        return jsonify(count=len(rows), product_ids=[row.product_id for row in rows])

    @application.after_request
    def optional_no_script(response):
        if request.args.get("fixture_no_script") == "1" and response.mimetype == "text/html":
            response.set_data(response.get_data(as_text=True).replace(
                '<script src="/static/js/market.js" defer></script>', ""))
        return response

    return application


if __name__ == "__main__":
    from waitress import serve
    print("MM-028 fixture: http://127.0.0.1:5028/products", flush=True)
    print("Login: shopper@recent-fixture.test / Recently viewed fixture passphrase!", flush=True)
    serve(build_preview(), host="127.0.0.1", port=5028, threads=8)
