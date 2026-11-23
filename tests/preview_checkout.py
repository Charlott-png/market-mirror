"""Loopback-only MM-025 browser fixture; never reads the real database."""

from decimal import Decimal
from pathlib import Path
import tempfile

from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import CartItem, Product, User


PASSWORD = "Checkout demo passphrase!"


def build_preview():
    root = Path(__file__).resolve().parents[1] / ".pytest-tmp"
    root.mkdir(exist_ok=True)
    fixture_dir = Path(tempfile.mkdtemp(prefix="mm025-browser-", dir=root))
    application = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{(fixture_dir / 'checkout.sqlite').as_posix()}",
        "UPLOAD_FOLDER": str(fixture_dir / "uploads"),
        "AI_FOLDER": str(fixture_dir / "ai"),
        "TEMPLATES_AUTO_RELOAD": True,
        "CHECKOUT_TOKEN_MAX_AGE": 1800,
    })
    with application.app_context():
        db.create_all()
        password_hash = generate_password_hash(PASSWORD)
        buyer = User(username="checkout-buyer", email="buyer@checkout.test",
                     password_hash=password_hash)
        other = User(username="other-buyer", email="other@checkout.test",
                     password_hash=password_hash)
        first_seller = User(username="laptop-seller", email="laptop@checkout.test",
                            password_hash=password_hash)
        second_seller = User(username="camera-seller", email="camera@checkout.test",
                             password_hash=password_hash)
        db.session.add_all([buyer, other, first_seller, second_seller])
        db.session.flush()
        products = [
            Product(seller_id=first_seller.id, title="Demo student laptop",
                description="A generated fixture laptop for the isolated checkout demonstration.",
                price=Decimal("120.50"), currency="USD", category="electronics",
                condition="good", status="active"),
            Product(seller_id=second_seller.id, title="Demo mirrorless camera",
                description="A generated fixture camera for the isolated checkout demonstration.",
                price=Decimal("79.45"), currency="USD", category="electronics",
                condition="like_new", status="active"),
        ]
        db.session.add_all(products)
        db.session.flush()
        for product in products:
            db.session.add(CartItem(user_id=buyer.id, product_id=product.id))
        db.session.add(CartItem(user_id=other.id, product_id=products[0].id))
        db.session.commit()
    return application


if __name__ == "__main__":
    from waitress import serve
    print("MM-025 fixture: http://127.0.0.1:5025/auth/login", flush=True)
    print("Buyer: buyer@checkout.test / Checkout demo passphrase!", flush=True)
    serve(build_preview(), host="127.0.0.1", port=5025)

