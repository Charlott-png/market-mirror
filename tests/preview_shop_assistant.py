"""Loopback-only MM-027 browser fixture; never reads the real database.

Run with: python -m tests.preview_shop_assistant
Stop with Ctrl+C. Temporary data remains under .pytest-tmp only.
"""

from decimal import Decimal
from pathlib import Path
import tempfile

from flask import jsonify
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import Product, User


PASSWORD = "Shop assistant fixture passphrase!"


class FixtureShopGenerator:
    def __init__(self):
        self.calls = []

    def __call__(self, query, history, catalogue, truncated):
        self.calls.append({
            "query_length": len(query),
            "history_messages": len(history),
            "candidate_ids": [item["id"] for item in catalogue],
            "truncated": truncated,
        })
        lowered = query.casefold()
        if "provider error" in lowered:
            raise RuntimeError("fixture provider body that must stay private")
        if "malformed" in lowered:
            return {"unexpected": "shape"}
        if "no match" in lowered:
            return {
                "summary": "I could not find an active product matching that request.",
                "recommendations": [],
                "follow_up": "Would you like to try a different budget or category?",
            }
        cameras = [item for item in catalogue if "camera" in item["title"].casefold()]
        cameras.sort(key=lambda item: Decimal(item["price"]))
        selected = cameras[:2]
        if "sold during" in lowered and selected:
            product = db.session.get(Product, selected[0]["id"])
            product.status = "sold"
            db.session.commit()
            selected = selected[:1]
        return {
            "summary": "I found active cameras ordered from the lowest price.",
            "recommendations": [{
                "product_id": item["id"],
                "reason": "This active camera is one of the lowest-priced matching listings.",
            } for item in selected],
            "follow_up": "Would you like to narrow the results by condition?",
        }


def build_preview():
    root = Path(__file__).resolve().parents[1] / ".pytest-tmp"
    root.mkdir(exist_ok=True)
    fixture_dir = Path(tempfile.mkdtemp(prefix="mm027-browser-", dir=root))
    generator = FixtureShopGenerator()
    application = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{(fixture_dir / 'assistant.sqlite').as_posix()}",
        "UPLOAD_FOLDER": str(fixture_dir / "uploads"),
        "AI_FOLDER": str(fixture_dir / "ai"),
        "TEMPLATES_AUTO_RELOAD": True,
        "SHOP_ASSISTANT_ENABLED": True,
        "SHOP_ASSISTANT_MODEL": "gemini-3.5-flash-lite",
        "SHOP_ASSISTANT_TIMEOUT_SECONDS": 12,
        "SHOP_ASSISTANT_GENERATOR": generator,
    })
    with application.app_context():
        db.create_all()
        password_hash = generate_password_hash(PASSWORD)
        shopper = User(
            username="assistant-shopper", email="shopper@assistant-fixture.test",
            password_hash=password_hash)
        seller = User(
            username="fixture-seller", email="seller@assistant-fixture.test",
            password_hash=password_hash)
        db.session.add_all([shopper, seller])
        db.session.flush()
        db.session.add_all([
            Product(seller_id=seller.id, title="Budget student camera",
                description="A compact digital camera for classroom projects.",
                price=Decimal("39.90"), currency="USD", category="electronics",
                condition="good", status="active"),
            Product(seller_id=seller.id, title="Mirrorless travel camera",
                description="A like-new camera with controls for photography practice.",
                price=Decimal("149.00"), currency="USD", category="electronics",
                condition="like_new", status="active"),
            Product(seller_id=seller.id, title="Camping tent",
                description="A lightweight tent for two people.",
                price=Decimal("45.00"), currency="USD", category="sports_outdoors",
                condition="good", status="active"),
            Product(seller_id=seller.id, title="Sold hidden camera",
                description="This sold item must never enter provider context.",
                price=Decimal("10.00"), currency="USD", category="electronics",
                condition="fair", status="sold"),
            Product(seller_id=seller.id, title="Archived private item",
                description="This archived item must never enter provider context.",
                price=Decimal("5.00"), currency="USD", category="other",
                condition="fair", status="archived"),
        ])
        db.session.commit()

    @application.get("/fixture-mm027-state")
    def fixture_state():
        return jsonify(calls=len(generator.calls),
                       last=generator.calls[-1] if generator.calls else None)

    return application


if __name__ == "__main__":
    from waitress import serve
    print("MM-027 fixture: http://127.0.0.1:5027/", flush=True)
    print("Login: shopper@assistant-fixture.test / Shop assistant fixture passphrase!", flush=True)
    serve(build_preview(), host="127.0.0.1", port=5027, threads=8)
