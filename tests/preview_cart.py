"""Loopback-only MM-019 browser fixture; never reads the real database.

Run with: python -m tests.preview_cart
Stop with Ctrl+C. Temporary data remains under .pytest-tmp only.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import tempfile

from flask import request
from PIL import Image
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import CartItem, Product, SavedProduct, User


PASSWORD = "Cart demo passphrase!"


def build_preview():
    root = Path(__file__).resolve().parents[1] / ".pytest-tmp"
    root.mkdir(exist_ok=True)
    fixture_dir = Path(tempfile.mkdtemp(prefix="mm019-browser-", dir=root))
    uploads = fixture_dir / "uploads"
    uploads.mkdir()
    image_name = "9" * 32 + ".jpg"
    Image.new("RGB", (900, 600), "#4f7d68").save(uploads / image_name)
    application = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{(fixture_dir / 'cart.sqlite').as_posix()}",
        "UPLOAD_FOLDER": str(uploads),
        "AI_FOLDER": str(fixture_dir / "ai"),
        "TEMPLATES_AUTO_RELOAD": True,
    })
    with application.app_context():
        db.create_all()
        password_hash = generate_password_hash(PASSWORD)
        seller = User(username="cart-seller", email="seller@cart.test", password_hash=password_hash)
        buyer = User(username="cart-buyer", email="buyer@cart.test", password_hash=password_hash)
        second = User(username="second-buyer", email="second@cart.test", password_hash=password_hash)
        busy = User(username="busy-buyer", email="busy@cart.test", password_hash=password_hash)
        db.session.add_all([seller, buyer, second, busy])
        db.session.flush()
        created = datetime(2026, 1, 1, tzinfo=timezone.utc)
        products = []
        for index in range(12):
            product = Product(
                seller_id=seller.id,
                title=("Extra-long demonstration backpack title that wraps safely on a small screen"
                       if index == 0 else f"Cart demonstration item {index + 1:02d}"),
                description="An isolated cart browser fixture product, not a real marketplace listing.",
                price=Decimal(f"{10 + index}.25"),
                currency="USD",
                category="other",
                condition="good",
                status="active",
                image_filename=image_name if index % 2 == 0 else None,
                created_at=created + timedelta(minutes=index),
            )
            products.append(product)
            db.session.add(product)
        db.session.flush()
        db.session.add(SavedProduct(user_id=buyer.id, product_id=products[2].id))
        for index, product in enumerate(products):
            db.session.add(CartItem(user_id=busy.id, product_id=product.id,
                                    added_at=created + timedelta(minutes=index)))
        products[-1].title = "ARCHIVED_PRIVATE_CART_CANARY"
        products[-1].status = "archived"
        db.session.commit()

    @application.after_request
    def optional_no_script(response):
        if request.args.get("fixture_no_script") == "1" and response.mimetype == "text/html":
            response.set_data(response.get_data(as_text=True).replace(
                '<script src="/static/js/market.js" defer></script>', ""))
        return response

    return application


if __name__ == "__main__":
    from waitress import serve
    print("MM-019 fixtures: http://127.0.0.1:5019/products", flush=True)
    serve(build_preview(), host="127.0.0.1", port=5019)
