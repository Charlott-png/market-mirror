"""Loopback-only MM-020 browser fixture; never reads the real database.

Run with: python -m tests.preview_live_search
Stop with Ctrl+C. Temporary data remains under .pytest-tmp only.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import tempfile
import time

from flask import Response, jsonify, request
from PIL import Image
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import Product, User


PASSWORD = "Live search demo passphrase!"


def build_preview():
    root = Path(__file__).resolve().parents[1] / ".pytest-tmp"
    root.mkdir(exist_ok=True)
    fixture_dir = Path(tempfile.mkdtemp(prefix="mm020-browser-", dir=root))
    uploads = fixture_dir / "uploads"
    uploads.mkdir()
    image_name = "2" * 32 + ".jpg"
    Image.new("RGB", (900, 600), "#427a91").save(uploads / image_name)
    application = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{(fixture_dir / 'live-search.sqlite').as_posix()}",
        "UPLOAD_FOLDER": str(uploads),
        "AI_FOLDER": str(fixture_dir / "ai"),
        "TEMPLATES_AUTO_RELOAD": True,
    })

    with application.app_context():
        db.create_all()
        password_hash = generate_password_hash(PASSWORD)
        seller = User(username="live-seller", email="seller@live-search.test",
                      password_hash=password_hash)
        buyer = User(username="live-buyer", email="buyer@live-search.test",
                     password_hash=password_hash)
        db.session.add_all([seller, buyer])
        db.session.flush()
        created = datetime(2026, 1, 1, tzinfo=timezone.utc)
        special = [
            ("Slow ceramic study lamp", "home_garden", "good", "18.50"),
            ("Fast digital camera", "electronics", "like_new", "220.00"),
            ("Silver student laptop", "electronics", "good", "450.00"),
            ("Extra-long live-search demonstration backpack title that wraps on narrow screens",
             "clothing", "good", "25.00"),
        ]
        for index in range(25):
            if index < len(special):
                title, category, condition, price = special[index]
            else:
                title, category, condition, price = (
                    f"Browser fixture product {index + 1:02d}", "other", "good", f"{30 + index}.25")
            db.session.add(Product(
                seller_id=seller.id,
                title=title,
                description="Isolated AJAX browser fixture product, never part of the real marketplace.",
                price=Decimal(price),
                currency="USD",
                category=category,
                condition=condition,
                status="active",
                image_filename=image_name if index % 3 == 0 else None,
                created_at=created + timedelta(minutes=index),
            ))
        db.session.add(Product(seller_id=seller.id, title="SOLD_AJAX_PRIVATE_CANARY",
            description="Never public.", price=Decimal("1.00"), currency="USD", category="other",
            condition="fair", status="sold", created_at=created + timedelta(days=1)))
        db.session.add(Product(seller_id=seller.id, title="ARCHIVED_AJAX_PRIVATE_CANARY",
            description="Never public.", price=Decimal("1.00"), currency="USD", category="other",
            condition="fair", status="archived", created_at=created + timedelta(days=1)))
        db.session.commit()

    @application.before_request
    def controlled_live_search_conditions():
        if request.path != "/products/search":
            return None
        query = request.args.get("q", "")
        if query == "slow":
            time.sleep(1.2)
        elif query == "failurefixture":
            return jsonify(error="Controlled browser-fixture failure."), 503
        elif query == "malformedfixture":
            return Response("{", status=200, mimetype="application/json")
        return None

    @application.after_request
    def optional_no_script(response):
        if request.args.get("fixture_no_script") == "1" and response.mimetype == "text/html":
            response.set_data(response.get_data(as_text=True).replace(
                '<script src="/static/js/market.js" defer></script>', ""))
        return response

    return application


if __name__ == "__main__":
    from waitress import serve
    print("MM-020 fixtures: http://127.0.0.1:5020/products", flush=True)
    serve(build_preview(), host="127.0.0.1", port=5020, threads=8)
