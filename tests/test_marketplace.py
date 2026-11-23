"""Acceptance tests for approved MM-003–010, written before feature code."""

from decimal import Decimal
from io import BytesIO
import re

import pytest
from werkzeug.security import check_password_hash, generate_password_hash

PASSWORD = "A long classroom passphrase!"


@pytest.fixture
def web(db_app):
    db_app.config.update(WTF_CSRF_ENABLED=False, SECRET_KEY="isolated-test-secret")
    return db_app.test_client()


@pytest.fixture
def accounts(user_factory):
    password_hash = generate_password_hash(PASSWORD)
    return [user_factory(username=name, email=f"{name}@example.test", password_hash=password_hash)
            for name in ("seller-one", "buyer-two", "stranger-three")]


def sign_in(client, user):
    with client.session_transaction() as session:
        session.clear()
        session["_user_id"] = str(user.id)
        session["_fresh"] = True
        session["login_at"] = 2000000000


def listing_data(**changes):
    data = dict(title="Useful study lamp", description="A clean lamp suitable for a study desk.",
                price="19.99", category="home_garden", condition="good", request_token="new-form-1")
    data.update(changes)
    return data


def test_register_login_logout_profile(web, db_session):
    from app.models import User
    response = web.post("/auth/register", data=dict(username=" Student ", email=" STUDENT@EXAMPLE.TEST ",
        password=PASSWORD, confirm_password=PASSWORD))
    assert response.status_code == 302
    user = db_session.query(User).filter_by(username="student").one()
    assert user.email == "student@example.test"
    assert check_password_hash(user.password_hash, PASSWORD)
    assert web.post("/auth/login", data=dict(email=user.email, password=PASSWORD)).status_code == 302
    assert web.get("/account/profile").status_code == 200
    assert web.post("/account/profile", data={"bio": "Learning Python"}).status_code == 302
    db_session.refresh(user)
    assert user.bio == "Learning Python"
    assert web.get("/auth/logout").status_code == 405
    assert web.post("/auth/logout").status_code == 302
    assert web.get("/account/profile").status_code == 302


@pytest.mark.parametrize("field,value", [("username", "ab"), ("email", "not-an-email"),
    ("password", "short"), ("password", "x" * 129), ("confirm_password", "different")])
def test_invalid_registration_has_no_partial_user(web, db_session, field, value):
    from app.models import User
    data = dict(username="student", email="student@example.test", password=PASSWORD, confirm_password=PASSWORD)
    data[field] = value
    response = web.post("/auth/register", data=data)
    assert response.status_code == 400
    assert db_session.query(User).count() == 0
    assert PASSWORD.encode() not in response.data


def test_duplicate_registration_and_generic_login(web, accounts, db_session):
    from app.models import User
    response = web.post("/auth/register", data=dict(username="SELLER-ONE", email="new@example.test",
                       password=PASSWORD, confirm_password=PASSWORD))
    assert response.status_code == 400
    assert db_session.query(User).count() == 3
    for email in (accounts[0].email, "missing@example.test"):
        response = web.post("/auth/login", data=dict(email=email, password="wrong"))
        assert response.status_code == 400
        assert b"Invalid email or password" in response.data


@pytest.mark.parametrize("target", ["https://evil.example/", "//evil.example/", "/\\evil.example", "javascript:alert(1)"])
def test_login_redirect_is_local(web, accounts, target):
    response = web.post("/auth/login", query_string={"next": target},
                        data=dict(email=accounts[0].email, password=PASSWORD))
    assert response.status_code == 302
    assert response.location.startswith("/") and not response.location.startswith("//")
    assert "evil.example" not in response.location


def test_expired_session_and_login_limit(web, accounts, db_app):
    now = [2000000000.0]
    db_app.config["CLOCK"] = lambda: now[0]
    for _ in range(5):
        assert web.post("/auth/login", data=dict(email=accounts[0].email, password="wrong")).status_code == 400
    response = web.post("/auth/login", data=dict(email=accounts[0].email, password=PASSWORD))
    assert response.status_code == 429 and "Retry-After" in response.headers
    now[0] += 901
    assert web.post("/auth/login", data=dict(email=accounts[0].email, password=PASSWORD)).status_code == 302
    now[0] += 8 * 3600 + 1
    assert web.get("/account/profile").status_code == 302


def test_csrf_real_form_token_required(web, db_app):
    db_app.config["WTF_CSRF_ENABLED"] = True
    data = dict(username="csrf-user", email="csrf@example.test", password=PASSWORD, confirm_password=PASSWORD)
    assert web.post("/auth/register", data=data).status_code == 400
    page = web.get("/auth/register").get_data(as_text=True)
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', page)
    assert match
    data["csrf_token"] = match.group(1)
    assert web.post("/auth/register", data=data).status_code == 302


def test_listing_creation_idempotency_and_owner_identity(web, accounts, db_session):
    from app.models import Product
    sign_in(web, accounts[0])
    data = listing_data(seller_id=str(accounts[1].id), currency="EUR", status="sold")
    first = web.post("/listings/new", data=data)
    second = web.post("/listings/new", data=data)
    assert first.status_code == second.status_code == 302
    assert first.location == second.location
    product = db_session.query(Product).one()
    assert product.seller_id == accounts[0].id
    assert product.status == "active" and product.currency == "USD"
    assert product.price == Decimal("19.99")


@pytest.mark.parametrize("price", ["0", "-1", "1.001", "NaN", "Infinity", "$5", "1,000", "10000000.00"])
def test_listing_bad_prices_no_row(web, accounts, db_session, price):
    from app.models import Product
    sign_in(web, accounts[0])
    response = web.post("/listings/new", data=listing_data(price=price))
    assert response.status_code == 400
    assert b"Useful study lamp" in response.data
    assert db_session.query(Product).count() == 0


def test_edit_permission_stale_version_and_archival(web, accounts, product_factory, db_session):
    product = product_factory(seller=accounts[0])
    product_id = product.id
    sign_in(web, accounts[1])
    assert web.get(f"/listings/{product_id}/edit").status_code == 404
    assert web.get(f"/listings/{product_id}/preview").status_code == 404
    assert web.post(f"/listings/{product_id}/status", data={"status": "sold", "version": 1}).status_code == 404
    sign_in(web, accounts[0])
    original_version = product.version
    assert web.post(f"/listings/{product_id}/edit", data=listing_data(version=original_version)).status_code == 302
    assert web.post(f"/listings/{product_id}/edit", data=listing_data(version=original_version, title="Stale title")).status_code == 409
    db_session.refresh(product)
    assert product.title == "Useful study lamp"
    assert web.post(f"/listings/{product_id}/status", data={"status": "archived", "version": product.version}).status_code == 302
    db_session.refresh(product)
    assert product.status == "archived"


@pytest.mark.parametrize("source,target,allowed", [("active", "sold", True), ("active", "archived", True),
    ("sold", "archived", True), ("archived", "active", True), ("sold", "active", False),
    ("archived", "sold", False), ("active", "active", True)])
def test_listing_status_transitions(web, accounts, product_factory, db_session, source, target, allowed):
    product = product_factory(seller=accounts[0], status=source)
    sign_in(web, accounts[0])
    response = web.post(f"/listings/{product.id}/status", data={"status": target, "version": product.version})
    assert response.status_code == (302 if allowed else 400)
    db_session.refresh(product)
    assert product.status == (target if allowed else source)


def picture():
    from PIL import Image
    stream = BytesIO()
    Image.new("RGB", (80, 40), "blue").save(stream, format="PNG")
    stream.seek(0)
    return stream


def test_safe_image_and_archived_media(web, accounts, db_session, db_app, tmp_path):
    from app.models import Product
    db_app.config["UPLOAD_FOLDER"] = str(tmp_path / "uploads")
    sign_in(web, accounts[0])
    data = listing_data(image=(picture(), "../../CON.png"))
    assert web.post("/listings/new", data=data, content_type="multipart/form-data").status_code == 302
    product = db_session.query(Product).one()
    assert product.image_filename.endswith(".jpg") and "/" not in product.image_filename
    media_url = f"/media/products/{product.image_filename}"
    assert web.get(media_url).mimetype == "image/jpeg"
    assert web.post(f"/listings/{product.id}/status", data={"status": "archived", "version": product.version}).status_code == 302
    assert web.get(media_url).status_code == 200
    sign_in(web, accounts[1])
    assert web.get(media_url).status_code == 404


def test_corrupt_image_rejected_without_files(web, accounts, db_session, db_app, tmp_path):
    from app.models import Product
    root = tmp_path / "images"
    db_app.config["UPLOAD_FOLDER"] = str(root)
    sign_in(web, accounts[0])
    data = listing_data(image=(BytesIO(b"<script>alert(1)</script>"), "safe.jpg"))
    assert web.post("/listings/new", data=data).status_code == 400
    assert db_session.query(Product).count() == 0
    assert not root.exists() or not list(root.iterdir())


def test_search_visibility_literal_matching_and_filters(web, accounts, product_factory):
    product_factory(seller=accounts[0], title="100% cotton shirt", category="clothing", price=Decimal("15.00"))
    product_factory(seller=accounts[0], title="100 percent cotton", category="clothing")
    product_factory(seller=accounts[0], title="Hidden canary listing", status="archived")
    response = web.get("/products", query_string={"q": "%"})
    assert response.status_code == 200
    assert b"100% cotton shirt" in response.data and b"100 percent cotton" not in response.data
    response = web.get("/products", query_string={"category": "clothing", "max_price": "20"})
    assert b"100% cotton shirt" in response.data and b"100 percent cotton" not in response.data
    assert b"Hidden canary listing" not in web.get("/products").data


@pytest.mark.parametrize("query", ["page=0", "page=-1", "page=x", "sort=bad", "category=bad",
    "min_price=5&max_price=1", "q=a&q=b", "page=1&page=2", "q=" + "x" * 121])
def test_search_invalid_parameters(web, query):
    assert web.get("/products?" + query).status_code == 400


def test_public_detail_and_seller_privacy(web, accounts, product_factory):
    active = product_factory(seller=accounts[0])
    sold = product_factory(seller=accounts[0], status="sold")
    archived = product_factory(seller=accounts[0], status="archived")
    assert web.get(f"/products/{active.id}").status_code == 200
    assert b"Sold" in web.get(f"/products/{sold.id}").data
    assert web.get(f"/products/{archived.id}").status_code == 404
    page = web.get(f"/sellers/{accounts[0].username}")
    assert page.status_code == 200
    assert accounts[0].email.encode() not in page.data
    assert accounts[0].password_hash.encode() not in page.data


def test_message_journey_permissions_replay_and_read_markers(web, accounts, product_factory, db_session):
    from app.models import Conversation, Message, ReadMarker
    product = product_factory(seller=accounts[0])
    sign_in(web, accounts[1])
    data = dict(body="Is this available? <script>bad()</script>", request_token="contact-first")
    first = web.post(f"/products/{product.id}/contact", data=data)
    assert first.status_code == 302
    assert web.post(f"/products/{product.id}/contact", data=data).location == first.location
    conversation = db_session.query(Conversation).one()
    assert db_session.query(Message).count() == 1
    page = web.get(first.location)
    assert b"&lt;script&gt;" in page.data and b"<script>bad()" not in page.data
    sign_in(web, accounts[2])
    assert web.get(first.location).status_code == 404
    assert web.post(first.location + "/send", data={"body": "intrusion", "request_token": "intrude"}).status_code == 404
    sign_in(web, accounts[0])
    assert web.post(first.location + "/send", data={"body": "Yes!", "request_token": "reply", "sender_id": accounts[2].id}).status_code == 302
    latest = db_session.query(Message).order_by(Message.id.desc()).first()
    assert latest.sender_id == accounts[0].id
    assert web.post(first.location + "/read", data={"message_id": latest.id}).status_code == 302
    assert db_session.query(ReadMarker).filter_by(conversation_id=conversation.id, user_id=accounts[0].id).one().last_read_message_id == latest.id
    assert db_session.query(ReadMarker).filter_by(user_id=accounts[1].id).count() == 0


def test_contact_self_sold_and_archived_reply_policy(web, accounts, product_factory, db_session):
    from app.models import Conversation, Message
    product = product_factory(seller=accounts[0])
    sign_in(web, accounts[0])
    assert web.post(f"/products/{product.id}/contact", data={"body": "self", "request_token": "one"}).status_code == 400
    sign_in(web, accounts[1])
    assert web.post(f"/products/{product.id}/contact", data={"body": "hello", "request_token": "two"}).status_code == 302
    conversation = db_session.query(Conversation).one()
    product.status = "sold"
    db_session.commit()
    assert web.post(f"/messages/{conversation.id}/send", data={"body": "still replying", "request_token": "three"}).status_code == 302
    sign_in(web, accounts[2])
    assert web.post(f"/products/{product.id}/contact", data={"body": "new contact", "request_token": "four"}).status_code == 400
    product.status = "archived"
    db_session.commit()
    sign_in(web, accounts[1])
    assert web.post(f"/messages/{conversation.id}/send", data={"body": "blocked", "request_token": "five"}).status_code == 400
    assert web.get(f"/messages/{conversation.id}").status_code == 200
    assert db_session.query(Message).count() == 2


def test_save_replay_unavailable_placeholder_and_own_save(web, accounts, product_factory, db_session):
    from app.models import SavedProduct
    product = product_factory(seller=accounts[0], title="Private title canary")
    sign_in(web, accounts[0])
    assert web.post(f"/products/{product.id}/save").status_code == 400
    sign_in(web, accounts[1])
    for _ in range(2):
        assert web.post(f"/products/{product.id}/save").status_code == 302
    assert db_session.query(SavedProduct).count() == 1
    assert web.get(f"/products/{product.id}/save").status_code == 405
    product.status = "archived"
    db_session.commit()
    page = web.get("/saved")
    assert b"Unavailable product" in page.data and b"Private title canary" not in page.data
    for _ in range(2):
        assert web.post(f"/products/{product.id}/unsave").status_code == 302
    assert db_session.query(SavedProduct).count() == 0


def test_event_consent_deduplication_and_optout(web, accounts, product_factory, db_session):
    from app.models import InteractionEvent
    product = product_factory(seller=accounts[0])
    sign_in(web, accounts[1])
    assert web.post(f"/products/{product.id}/view").status_code == 204
    assert db_session.query(InteractionEvent).count() == 0
    assert web.post("/account/profile", data={"bio": "", "personalization": "y"}).status_code == 302
    for _ in range(2):
        assert web.post(f"/products/{product.id}/view").status_code == 204
    assert db_session.query(InteractionEvent).count() == 1
    assert web.post("/account/profile", data={"bio": ""}).status_code == 302
    assert db_session.query(InteractionEvent).count() == 0


def test_dashboard_is_private_and_empty_states(web, accounts, product_factory):
    product_factory(seller=accounts[0], title="Only seller sees private draft", status="archived")
    sign_in(web, accounts[1])
    page = web.get("/dashboard", query_string={"user_id": accounts[0].id})
    assert page.status_code == 200
    assert b"Only seller sees private draft" not in page.data
    assert b"No listings" in page.data
    sign_in(web, accounts[0])
    assert b"Only seller sees private draft" in web.get("/dashboard").data
