"""MM-019 contracts written before cart implementation; no real database use."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import re

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError

from tests.test_marketplace import sign_in
from tests.test_seller_profile import Page


@pytest.fixture()
def cart_web(db_app):
    db_app.config.update(WTF_CSRF_ENABLED=False, SECRET_KEY="isolated-cart-test-secret")
    return db_app.test_client()


def cart_item_model():
    """Import inside tests so the pre-implementation Red run still collects."""
    from app import models
    assert hasattr(models, "CartItem"), "MM-019 CartItem model is missing"
    return models.CartItem


def add_row(db_session, user, product, **changes):
    CartItem = cart_item_model()
    values = {"user_id": user.id, "product_id": product.id}
    values.update(changes)
    row = CartItem(**values)
    db_session.add(row)
    db_session.commit()
    return row


def table_snapshot(db_session):
    from app.extensions import db
    return {table.name: db_session.execute(select(table)).all()
            for table in db.metadata.sorted_tables}


def cart_count(page):
    return int(Page(page).one(id="cart-navigation-link")["attrs"]["data-cart-count"])


def csrf_for(html, action):
    form = re.search(rf'<form[^>]*action="{re.escape(action)}"[^>]*>(.*?)</form>', html, re.S)
    assert form, f"No form for {action}"
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', form.group(1))
    assert token
    return token.group(1)


def test_cart_item_model_constraints_and_utc(db_app, user_factory, product_factory, db_session):
    CartItem = cart_item_model()
    buyer = user_factory()
    product = product_factory()
    row = add_row(db_session, buyer, product)
    db_session.expire_all()
    stored = db_session.get(CartItem, (buyer.id, product.id))
    assert stored.product.id == product.id
    assert stored.added_at.tzinfo is not None
    db_session.expunge(stored)
    with pytest.raises(IntegrityError):
        db_session.add(CartItem(user_id=buyer.id, product_id=product.id))
        db_session.commit()
    db_session.rollback()
    assert db_session.query(CartItem).count() == 1


@pytest.mark.parametrize("bad_field", ["user_id", "product_id"])
def test_cart_item_foreign_keys_reject_missing_parents(db_app, user_factory, product_factory,
                                                       db_session, bad_field):
    CartItem = cart_item_model()
    buyer, product = user_factory(), product_factory()
    values = {"user_id": buyer.id, "product_id": product.id}
    values[bad_field] = 999999999
    with pytest.raises(IntegrityError):
        db_session.add(CartItem(**values))
        db_session.commit()
    db_session.rollback()
    assert db_session.query(CartItem).count() == 0


def test_cart_routes_require_login_and_mutations_are_post_only(cart_web, db_session):
    CartItem = cart_item_model()
    for path in ("/cart", "/cart/items/1", "/cart/items/1/remove", "/cart/checkout"):
        response = cart_web.get(path)
        if path == "/cart":
            assert response.status_code == 302 and "/auth/login" in response.location
        else:
            assert response.status_code == 405
    for path in ("/cart/items/1", "/cart/items/1/remove", "/cart/checkout"):
        response = cart_web.post(path)
        assert response.status_code == 302 and "/auth/login" in response.location
    assert db_session.query(CartItem).count() == 0


def test_add_success_replay_count_and_feature_separation(cart_web, user_factory, product_factory,
                                                         db_session):
    from app.models import InteractionEvent, SavedProduct
    CartItem = cart_item_model()
    buyer = user_factory()
    product = product_factory(title="Cart lamp")
    sign_in(cart_web, buyer)
    first = cart_web.post(f"/cart/items/{product.id}", data={"next": "/products"})
    second = cart_web.post(f"/cart/items/{product.id}", data={"next": "/products"})
    assert first.status_code == second.status_code == 302
    assert first.location == second.location == "/products"
    assert db_session.query(CartItem).filter_by(user_id=buyer.id, product_id=product.id).count() == 1
    assert db_session.query(SavedProduct).count() == 0
    assert db_session.query(InteractionEvent).count() == 0
    page = cart_web.get("/products")
    assert cart_count(page) == 1
    assert b"already in your cart" in page.data


@pytest.mark.parametrize("case,expected", [
    ("own", 400), ("sold", 400), ("archived", 404), ("disabled-seller", 400), ("missing", 404),
])
def test_add_rejects_ineligible_products(cart_web, user_factory, product_factory, db_session,
                                         case, expected):
    CartItem = cart_item_model()
    buyer, seller = user_factory(), user_factory()
    if case == "missing":
        product_id = 999999999
    else:
        product = product_factory(seller=buyer if case == "own" else seller,
                                  status=case if case in {"sold", "archived"} else "active")
        product_id = product.id
        if case == "disabled-seller":
            seller.enabled = False
            db_session.commit()
    sign_in(cart_web, buyer)
    response = cart_web.post(f"/cart/items/{product_id}")
    assert response.status_code == expected
    assert db_session.query(CartItem).count() == 0


def test_two_simultaneous_adds_make_one_row(db_app, user_factory, product_factory, db_session):
    CartItem = cart_item_model()
    db_app.config["WTF_CSRF_ENABLED"] = False
    buyer, product = user_factory(), product_factory()
    uid, pid = buyer.id, product.id
    clients = [db_app.test_client(), db_app.test_client()]
    for client in clients:
        sign_in(client, buyer)
    db_session.remove()
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda c: c.post(f"/cart/items/{pid}"), clients))
    assert [response.status_code for response in responses] == [302, 302]
    assert db_session.query(CartItem).filter_by(user_id=uid, product_id=pid).count() == 1


@pytest.mark.parametrize("target", [
    "https://evil.example/steal", "//evil.example/steal", "/\\evil.example", "javascript:alert(1)"
])
def test_add_redirect_never_leaves_site(cart_web, user_factory, product_factory, target):
    buyer, product = user_factory(), product_factory()
    sign_in(cart_web, buyer)
    response = cart_web.post(f"/cart/items/{product.id}", data={"next": target})
    assert response.status_code == 302
    assert response.location == "/cart"
    assert "evil.example" not in response.location


def test_cards_place_controls_in_approved_surfaces(cart_web, user_factory, product_factory,
                                                   db_session):
    from app.models import SavedProduct
    seller, buyer = user_factory(), user_factory()
    product = product_factory(seller=seller)
    add_path = f"/cart/items/{product.id}"
    anonymous = cart_web.get("/products").get_data(as_text=True)
    assert f'/auth/login?next=' in anonymous and "Sign in to add to cart" in anonymous
    assert f'action="{add_path}"' not in anonymous

    db_session.add(SavedProduct(user_id=buyer.id, product_id=product.id))
    db_session.commit()
    sign_in(cart_web, buyer)
    for path in ("/products", f"/sellers/{seller.username}", "/saved"):
        html = cart_web.get(path).get_data(as_text=True)
        assert f'action="{add_path}"' in html and "Add to Cart" in html

    sign_in(cart_web, seller)
    assert f'action="{add_path}"' not in cart_web.get("/dashboard").get_data(as_text=True)
    assert f'action="{add_path}"' not in cart_web.get(f"/sellers/{seller.username}").get_data(as_text=True)


def test_header_count_is_current_user_only_and_includes_unavailable(cart_web, user_factory,
                                                                   product_factory, db_session):
    first, second = user_factory(), user_factory()
    active, archived = product_factory(), product_factory(status="archived")
    add_row(db_session, first, active)
    add_row(db_session, first, archived)
    add_row(db_session, second, active)
    sign_in(cart_web, first)
    assert cart_count(cart_web.get("/")) == 2
    sign_in(cart_web, second)
    page = cart_web.get("/")
    assert cart_count(page) == 1
    assert first.username.encode() not in page.data


def test_cart_page_money_order_and_pagination(cart_web, user_factory, product_factory, db_session):
    buyer, seller = user_factory(), user_factory()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    products = [product_factory(seller=seller, title=f"Cart item {i:02d}",
                                price=Decimal("1.00")) for i in range(21)]
    for index, product in enumerate(products):
        add_row(db_session, buyer, product, added_at=start + timedelta(minutes=index))
    sign_in(cart_web, buyer)
    first = Page(cart_web.get("/cart"))
    second = Page(cart_web.get("/cart?page=2"))
    expected = [product.id for product in reversed(products)]
    first_ids = [int(node["attrs"]["data-product-id"])
                 for node in first.find(**{"class": "cart-item", "data-product-id": None})]
    # HTMLParser attribute matching cannot express any value; stable row IDs are the source of truth.
    first_ids = [int(node["attrs"]["id"].removeprefix("cart-item-"))
                 for node in first.find(**{"class": "cart-item"})]
    second_ids = [int(node["attrs"]["id"].removeprefix("cart-item-"))
                  for node in second.find(**{"class": "cart-item"})]
    assert first_ids == expected[:20] and second_ids == expected[20:]
    for page in (first, second):
        assert page.text(id="cart-item-count") == "21 items in cart"
        assert page.text(id="cart-subtotal") == "$21.00 USD"
    assert first.find("a", href="/cart?page=2") and second.find("a", href="/cart?page=1")


def test_cart_uses_exact_decimal_subtotal(cart_web, user_factory, product_factory, db_session):
    buyer = user_factory()
    first = product_factory(price=Decimal("0.10"))
    second = product_factory(price=Decimal("0.20"))
    add_row(db_session, buyer, first)
    add_row(db_session, buyer, second)
    sign_in(cart_web, buyer)
    page = Page(cart_web.get("/cart"))
    assert page.text(id="cart-subtotal") == "$0.30 USD"


@pytest.mark.parametrize("status", ["sold", "archived"])
def test_unavailable_rows_are_private_counted_and_block_checkout(cart_web, user_factory,
                                                                 product_factory, db_session, status):
    CartItem = cart_item_model()
    buyer = user_factory()
    product = product_factory(title="PRIVATE_CART_TITLE_CANARY", description="PRIVATE CART DESCRIPTION")
    seller_email = product.seller.email
    add_row(db_session, buyer, product)
    product.status = status
    db_session.commit()
    sign_in(cart_web, buyer)
    page = cart_web.get("/cart")
    html = page.get_data(as_text=True)
    assert page.status_code == 200
    assert "Unavailable product" in html
    assert "PRIVATE_CART_TITLE_CANARY" not in html and seller_email not in html
    parsed = Page(page)
    assert parsed.text(id="cart-item-count") == "1 item in cart"
    assert parsed.text(id="cart-subtotal") == "$0.00 USD"
    assert parsed.find(id="cart-unavailable-warning")
    before = table_snapshot(db_session)
    checkout = cart_web.post("/cart/checkout")
    assert checkout.status_code == 409
    assert b"PRIVATE_CART_TITLE_CANARY" not in checkout.data
    assert table_snapshot(db_session) == before
    assert db_session.query(CartItem).count() == 1


def test_remove_is_scoped_idempotent_and_separate_from_saved(cart_web, user_factory,
                                                             product_factory, db_session):
    from app.models import SavedProduct
    CartItem = cart_item_model()
    victim, attacker = user_factory(), user_factory()
    product = product_factory()
    add_row(db_session, victim, product)
    db_session.add(SavedProduct(user_id=victim.id, product_id=product.id))
    db_session.commit()
    sign_in(cart_web, attacker)
    assert cart_web.post(f"/cart/items/{product.id}/remove").status_code == 302
    assert db_session.query(CartItem).filter_by(user_id=victim.id).count() == 1
    sign_in(cart_web, victim)
    for _ in range(2):
        assert cart_web.post(f"/cart/items/{product.id}/remove").status_code == 302
    assert db_session.query(CartItem).count() == 0
    assert db_session.query(SavedProduct).filter_by(user_id=victim.id, product_id=product.id).count() == 1
    assert product.status == "active"


def test_account_isolation_and_forged_fields(cart_web, user_factory, product_factory, db_session):
    CartItem = cart_item_model()
    victim, attacker = user_factory(), user_factory()
    victim_product = product_factory(title="VICTIM_CART_CANARY")
    attacker_product = product_factory(title="Attacker choice")
    add_row(db_session, victim, victim_product)
    sign_in(cart_web, attacker)
    page = cart_web.get("/cart")
    assert b"VICTIM_CART_CANARY" not in page.data and cart_count(page) == 0
    response = cart_web.post(f"/cart/items/{attacker_product.id}", data={
        "user_id": victim.id, "price": "0.01", "status": "sold", "quantity": "999",
    })
    assert response.status_code == 302
    assert db_session.query(CartItem).filter_by(user_id=attacker.id,
        product_id=attacker_product.id).count() == 1
    assert db_session.query(CartItem).filter_by(user_id=victim.id).count() == 1


def test_empty_and_valid_checkout_create_one_order_and_empty_cart(cart_web, user_factory,
                                                                 product_factory, db_session):
    CartItem = cart_item_model()
    from app import models
    assert hasattr(models, "Order"), "MM-025 Order model is missing"
    Order, OrderItem = models.Order, models.OrderItem
    buyer = user_factory()
    sign_in(cart_web, buyer)
    empty_page = cart_web.get("/cart")
    assert empty_page.status_code == 200 and b"Your cart is empty" in empty_page.data
    before_empty = table_snapshot(db_session)
    empty_checkout = cart_web.post("/cart/checkout")
    assert empty_checkout.status_code == 400
    assert table_snapshot(db_session) == before_empty

    products = [product_factory(price=Decimal("12.50")), product_factory(price=Decimal("7.25"))]
    for product in products:
        add_row(db_session, buyer, product)
    page = cart_web.get("/cart")
    token = re.search(r'name="checkout_token"[^>]*value="([^"]+)"',
                      page.get_data(as_text=True))
    assert token
    response = cart_web.post("/cart/checkout", data={"checkout_token": token.group(1)})
    assert response.status_code == 303
    assert db_session.query(Order).count() == 1
    assert db_session.query(OrderItem).count() == 2
    assert db_session.query(Order).one().total_amount == Decimal("19.75")
    assert db_session.query(CartItem).count() == 0
    assert all(product.status == "sold" for product in products)
    receipt = cart_web.get(response.location)
    assert b"Thank you for your purchase" in receipt.data
    assert b"$19.75 USD" in receipt.data


@pytest.mark.parametrize("page", ["0", "-1", "", "x", "1.5", "123456789", "1&page=2"])
def test_cart_rejects_invalid_pages(cart_web, user_factory, page):
    sign_in(cart_web, user_factory())
    assert cart_web.get(f"/cart?page={page}").status_code == 400


def test_real_csrf_protects_cart_mutations(db_app, user_factory, product_factory, db_session):
    CartItem = cart_item_model()
    buyer, product = user_factory(), product_factory()
    client = db_app.test_client()
    sign_in(client, buyer)
    products_html = client.get("/products").get_data(as_text=True)
    add_path = f"/cart/items/{product.id}"
    token = csrf_for(products_html, add_path)
    assert client.post(add_path).status_code == 400
    assert client.post(add_path, data={"csrf_token": token}).status_code == 302
    assert db_session.query(CartItem).count() == 1
    assert client.post(f"/cart/items/{product.id}/remove").status_code == 400
    assert client.post("/cart/checkout").status_code == 400
    assert db_session.query(CartItem).count() == 1


def test_add_commit_failure_rolls_back_without_false_success(db_app, user_factory,
                                                            product_factory, db_session, monkeypatch):
    CartItem = cart_item_model()
    db_app.config["WTF_CSRF_ENABLED"] = False
    buyer, product = user_factory(), product_factory()
    client = db_app.test_client()
    sign_in(client, buyer)
    with monkeypatch.context() as patch:
        def fail():
            raise OperationalError("private-cart-path", {}, Exception("private-cart-canary"))
        patch.setattr(db_session, "commit", fail)
        response = client.post(f"/cart/items/{product.id}")
    assert response.status_code == 503
    assert b"private-cart-canary" not in response.data
    assert db_session.query(CartItem).count() == 0

