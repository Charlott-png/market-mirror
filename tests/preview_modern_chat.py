"""Loopback-only MM-029 browser fixture; never reads the real database.

Run with: python -m tests.preview_modern_chat
Stop with Ctrl+C. Temporary data remains under .pytest-tmp only.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import secrets
import tempfile

from flask import redirect, render_template_string, request, url_for
from werkzeug.security import generate_password_hash

from app import create_app
from app.extensions import db
from app.models import Conversation, Message, Product, User


PASSWORD = "Modern chat fixture passphrase!"


def build_preview():
    root = Path(__file__).resolve().parents[1] / ".pytest-tmp"
    root.mkdir(exist_ok=True)
    fixture_dir = Path(tempfile.mkdtemp(prefix="mm029-browser-", dir=root))
    application = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": True,
        "SECRET_KEY": "isolated-mm029-browser-secret",
        "SQLALCHEMY_DATABASE_URI":
            f"sqlite:///{(fixture_dir / 'modern-chat.sqlite').as_posix()}",
        "UPLOAD_FOLDER": str(fixture_dir / "uploads"),
        "AI_FOLDER": str(fixture_dir / "ai"),
        "TEMPLATES_AUTO_RELOAD": True,
    })
    with application.app_context():
        db.create_all()
        password_hash = generate_password_hash(PASSWORD)
        seller = User(
            username="chat-fixture-seller",
            email="seller@chat-fixture.test",
            password_hash=password_hash,
        )
        buyer = User(
            username="chat-fixture-buyer",
            email="buyer@chat-fixture.test",
            password_hash=password_hash,
        )
        db.session.add_all([seller, buyer])
        db.session.flush()
        product = Product(
            seller_id=seller.id,
            title="Fixture digital camera",
            description="A temporary product for isolated chat verification.",
            price=Decimal("89.00"),
            currency="USD",
            category="electronics",
            condition="good",
            status="active",
        )
        db.session.add(product)
        db.session.flush()
        conversation = Conversation(
            product_id=product.id, buyer_id=buyer.id, seller_id=seller.id
        )
        db.session.add(conversation)
        db.session.flush()
        start = datetime(2026, 11, 7, 9, 0, tzinfo=timezone.utc)
        messages = []
        for index in range(55):
            messages.append(Message(
                conversation_id=conversation.id,
                sender_id=buyer.id if index % 2 == 0 else seller.id,
                body=("Buyer message " if index % 2 == 0 else "Seller reply ")
                    + f"{index + 1}: "
                    + ("longword" * 16 if index == 51 else "camera details ✓"),
                request_token=f"fixture-chat-{index}",
                created_at=start + timedelta(minutes=index),
            ))
        messages[-1].body = "Literal <script>never runs</script> and Unicode ✓"
        db.session.add_all(messages)
        db.session.commit()
        conversation_id = conversation.id
        seller_id = seller.id

    @application.get("/fixture-mm029-controls")
    def fixture_controls():
        return render_template_string(
            """<!doctype html><html lang="en"><head><title>MM-029 controls</title></head>
            <body><h1>MM-029 isolated controls</h1>
            <form method="post" action="{{ url_for('fixture_incoming') }}">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <button type="submit">Simulate incoming message</button></form></body></html>"""
        )

    @application.post("/fixture-mm029/incoming")
    def fixture_incoming():
        db.session.add(Message(
            conversation_id=conversation_id,
            sender_id=seller_id,
            body="New incoming message from the isolated seller.",
            request_token=f"fixture-incoming-{secrets.token_urlsafe(12)}",
        ))
        db.session.commit()
        return redirect(url_for("fixture_controls"))

    @application.after_request
    def optional_no_script(response):
        if request.args.get("fixture_no_script") == "1" and response.mimetype == "text/html":
            response.set_data(response.get_data(as_text=True).replace(
                '<script src="/static/js/conversation.js?v=mm029" defer></script>', ""))
        return response

    application.config["MM029_CONVERSATION_ID"] = conversation_id
    return application


if __name__ == "__main__":
    from waitress import serve

    app = build_preview()
    conversation_id = app.config["MM029_CONVERSATION_ID"]
    print(f"MM-029 fixture: http://127.0.0.1:5029/messages/{conversation_id}", flush=True)
    print("Login: buyer@chat-fixture.test / Modern chat fixture passphrase!", flush=True)
    print("Controls: http://127.0.0.1:5029/fixture-mm029-controls", flush=True)
    serve(app, host="127.0.0.1", port=5029, threads=8)

