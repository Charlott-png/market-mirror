"""Loopback-only MM-021 browser fixture; never reads the real database.

Run with: python -m tests.preview_mobile_navigation
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
from app.models import CartItem, Conversation, Message, Product, User


PASSWORD = "Mobile navigation demo passphrase!"


def build_preview():
    root = Path(__file__).resolve().parents[1] / ".pytest-tmp"
    root.mkdir(exist_ok=True)
    fixture_dir = Path(tempfile.mkdtemp(prefix="mm021-browser-", dir=root))
    uploads = fixture_dir / "uploads"
    uploads.mkdir()
    image_name = "3" * 32 + ".jpg"
    Image.new("RGB", (900, 600), "#2f7183").save(uploads / image_name)
    application = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{(fixture_dir / 'mobile-navigation.sqlite').as_posix()}",
        "UPLOAD_FOLDER": str(uploads),
        "AI_FOLDER": str(fixture_dir / "ai"),
        "TEMPLATES_AUTO_RELOAD": True,
    })

    with application.app_context():
        db.create_all()
        password_hash = generate_password_hash(PASSWORD)
        seller = User(username="mobile-seller", email="seller@mobile-navigation.test",
                      password_hash=password_hash)
        buyer = User(username="mobile-buyer", email="buyer@mobile-navigation.test",
                     password_hash=password_hash)
        db.session.add_all([seller, buyer])
        db.session.flush()
        created = datetime(2026, 1, 1, tzinfo=timezone.utc)
        products = []
        for index in range(25):
            product = Product(
                seller_id=seller.id,
                title=("Extra-long mobile demonstration backpack title that wraps safely"
                       if index == 0 else f"Mobile demonstration product {index + 1:02d}"),
                description="An isolated mobile browser fixture product, never part of the real marketplace.",
                price=Decimal(f"{20 + index}.25"),
                currency="USD",
                category="other",
                condition="good",
                status="active",
                image_filename=image_name if index % 3 == 0 else None,
                created_at=created + timedelta(minutes=index),
            )
            products.append(product)
            db.session.add(product)
        db.session.flush()
        for index, product in enumerate(products[:12]):
            db.session.add(CartItem(user_id=buyer.id, product_id=product.id,
                                    added_at=created + timedelta(minutes=index)))
        conversation = Conversation(product_id=products[0].id, buyer_id=buyer.id,
                                    seller_id=seller.id)
        db.session.add(conversation)
        db.session.flush()
        db.session.add(Message(conversation_id=conversation.id, sender_id=seller.id,
                               body="Temporary browser-check message.",
                               request_token="mm021-browser-message"))
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
    print("MM-021 fixture: http://127.0.0.1:5021/products", flush=True)
    print("Login: buyer@mobile-navigation.test / Mobile navigation demo passphrase!", flush=True)
    serve(build_preview(), host="127.0.0.1", port=5021, threads=8)
