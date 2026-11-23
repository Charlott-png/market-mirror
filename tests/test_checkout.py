"""MM-025 checkout contracts, written before application implementation."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import re

import pytest
from sqlalchemy.exc import IntegrityError, OperationalError

from tests.test_cart import add_row, cart_count, csrf_for
from tests.test_marketplace import sign_in


@pytest.fixture()
def checkout_web(db_app):
    db_app.config.update(WTF_CSRF_ENABLED=False,
                         SECRET_KEY="isolated-mm025-checkout-secret",
                         CHECKOUT_TOKEN_MAX_AGE=1800)
    return db_app.test_client()


def order_models():
    """Import inside tests so the Red suite can collect without MM-025 models."""
    from app import models
    assert hasattr(models, "Order"), "MM-025 Order model is missing"
    assert hasattr(models, "OrderItem"), "MM-025 OrderItem model is missing"
    return models.Order, models.OrderItem


def form_value(response, name):
    html = response.get_data(as_text=True)
    match = re.search(rf'name="{re.escape(name)}"[^>]*value="([^"]+)"', html)
    assert match, f"Expected {name} in the checkout form"
    return match.group(1)


def checkout(client, page=None, **extra):
    page = page or client.get("/cart")
    data = {"checkout_token": form_value(page, "checkout_token")}
    data.update(extra)
    return client.post("/cart/checkout", data=data), data["checkout_token"]


def test_order_models_store_exact_snapshots_and_reject_duplicate_product(
        db_app, user_factory, product_factory, db_session):
    Order, OrderItem = order_models()
    buyer, seller = user_factory(), user_factory()
    product = product_factory(seller=seller, title="Snapshot laptop",
                              price=Decimal("999.95"))
    order = Order(buyer_id=buyer.id, status="completed", total_amount=Decimal("999.95"),
                  currency="USD", checkout_nonce="a-valid-checkout-nonce-001")
    order.items.append(OrderItem(product_id=product.id, seller_id=seller.id,
        product_title=product.title, seller_username=seller.username,
        unit_price=product.price, currency="USD"))
    db_session.add(order)
    db_session.commit()
    db_session.expire_all()

    stored = db_session.get(Order, order.id)
    assert stored.buyer_id == buyer.id
    assert stored.total_amount == Decimal("999.95")
    assert stored.created_at.tzinfo is not None
    assert len(stored.items) == 1
    assert stored.items[0].product_title == "Snapshot laptop"
    assert stored.items[0].unit_price == Decimal("999.95")

    duplicate = Order(buyer_id=buyer.id, status="completed",
        total_amount=Decimal("999.95"), currency="USD",
        checkout_nonce="a-valid-checkout-nonce-002")
    duplicate.items.append(OrderItem(product_id=product.id, seller_id=seller.id,
        product_title=product.title, seller_username=seller.username,
        unit_price=product.price, currency="USD"))
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    assert db_session.query(Order).count() == 1


@pytest.mark.parametrize("field,value", [
    ("status", "pending"), ("currency", "EUR"),
    ("total_amount", Decimal("0.00")), ("checkout_nonce", "short"),
])
def test_order_model_rejects_invalid_values(db_app, user_factory, db_session, field, value):
    Order, _ = order_models()
    values = dict(buyer_id=user_factory().id, status="completed",
                  total_amount=Decimal("1.00"), currency="USD",
                  checkout_nonce="a-valid-checkout-nonce-003")
    values[field] = value
    with pytest.raises((ValueError, TypeError, IntegrityError)):
        db_session.add(Order(**values))
        db_session.commit()
    db_session.rollback()
    assert db_session.query(Order).count() == 0


def test_single_item_checkout_creates_order_sells_product_and_empties_cart(
        checkout_web, user_factory, product_factory, db_session):
    from app.models import CartItem
    Order, OrderItem = order_models()
    buyer, seller = user_factory(), user_factory()
    product = product_factory(seller=seller, title="Student laptop",
                              price=Decimal("450.25"))
    original_version = product.version
    add_row(db_session, buyer, product)
    sign_in(checkout_web, buyer)

    response, _ = checkout(checkout_web)
    assert response.status_code == 303
    order = db_session.query(Order).one()
    assert response.location == f"/orders/{order.id}/success"
    assert order.buyer_id == buyer.id and order.status == "completed"
    assert order.total_amount == Decimal("450.25") and order.currency == "USD"
    assert db_session.query(OrderItem).count() == 1
    assert order.items[0].product_title == "Student laptop"
    assert order.items[0].seller_username == seller.username
    db_session.refresh(product)
    assert product.status == "sold" and product.version == original_version + 1
    assert db_session.query(CartItem).filter_by(user_id=buyer.id).count() == 0

    receipt = checkout_web.get(response.location)
    assert receipt.status_code == 200
    assert b"Thank you for your purchase" in receipt.data
    assert b"Student laptop" in receipt.data and b"$450.25 USD" in receipt.data
    assert b"no real payment" in receipt.data.lower()
    assert cart_count(receipt) == 0


def test_multi_seller_checkout_uses_exact_total_and_preserves_other_relations(
        checkout_web, user_factory, product_factory, db_session):
    from app.models import CartItem, SavedProduct
    Order, OrderItem = order_models()
    buyer, other_buyer = user_factory(), user_factory()
    products = [product_factory(price=Decimal("0.10")),
                product_factory(price=Decimal("0.20"))]
    for product in products:
        add_row(db_session, buyer, product)
    add_row(db_session, other_buyer, products[0])
    db_session.add(SavedProduct(user_id=buyer.id, product_id=products[0].id))
    db_session.commit()
    sign_in(checkout_web, buyer)

    response, _ = checkout(checkout_web)
    assert response.status_code == 303
    order = db_session.query(Order).one()
    assert order.total_amount == Decimal("0.30")
    assert db_session.query(OrderItem).count() == 2
    assert db_session.query(CartItem).filter_by(user_id=buyer.id).count() == 0
    assert db_session.query(CartItem).filter_by(user_id=other_buyer.id).count() == 1
    assert db_session.query(SavedProduct).filter_by(user_id=buyer.id).count() == 1
    receipt = checkout_web.get(response.location)
    assert b"$0.30 USD" in receipt.data


def test_checkout_ignores_forged_business_fields(checkout_web, user_factory,
                                                  product_factory, db_session):
    Order, _ = order_models()
    buyer, victim = user_factory(), user_factory()
    product = product_factory(price=Decimal("75.00"), title="Server title")
    add_row(db_session, buyer, product)
    sign_in(checkout_web, buyer)
    page = checkout_web.get("/cart")
    response, _ = checkout(checkout_web, page, user_id=victim.id, buyer_id=victim.id,
        product_id=999999, seller_id=victim.id, price="0.01", total="0.01",
        currency="EUR", status="active")
    assert response.status_code == 303
    order = db_session.query(Order).one()
    assert order.buyer_id == buyer.id and order.total_amount == Decimal("75.00")
    assert order.items[0].product_id == product.id
    assert order.items[0].product_title == "Server title"
    assert order.currency == "USD" and product.status == "sold"


def test_stale_price_or_cart_change_rejects_everything(checkout_web, user_factory,
                                                       product_factory, db_session):
    from app.models import CartItem
    Order, _ = order_models()
    buyer = user_factory()
    products = [product_factory(price=Decimal("10.00")),
                product_factory(price=Decimal("20.00"))]
    for product in products:
        add_row(db_session, buyer, product)
    sign_in(checkout_web, buyer)
    page = checkout_web.get("/cart")
    products[0].price = Decimal("11.00")
    db_session.commit()

    response, _ = checkout(checkout_web, page)
    assert response.status_code == 409
    assert b"review" in response.data.lower()
    assert db_session.query(Order).count() == 0
    assert all(product.status == "active" for product in products)
    assert db_session.query(CartItem).filter_by(user_id=buyer.id).count() == 2


def test_unavailable_product_rejects_whole_checkout(checkout_web, user_factory,
                                                    product_factory, db_session):
    from app.models import CartItem
    Order, _ = order_models()
    buyer = user_factory()
    products = [product_factory(title="Still active"),
                product_factory(title="Private unavailable canary")]
    for product in products:
        add_row(db_session, buyer, product)
    sign_in(checkout_web, buyer)
    page = checkout_web.get("/cart")
    products[1].status = "archived"
    db_session.commit()

    response, _ = checkout(checkout_web, page)
    assert response.status_code == 409
    assert b"Private unavailable canary" not in response.data
    assert db_session.query(Order).count() == 0
    assert products[0].status == "active"
    assert db_session.query(CartItem).filter_by(user_id=buyer.id).count() == 2


def test_same_checkout_token_is_idempotent_and_cannot_buy_a_later_cart(
        checkout_web, user_factory, product_factory, db_session):
    from app.models import CartItem
    Order, _ = order_models()
    buyer = user_factory()
    first, later = product_factory(), product_factory()
    add_row(db_session, buyer, first)
    sign_in(checkout_web, buyer)
    page = checkout_web.get("/cart")
    first_response, token = checkout(checkout_web, page)
    assert first_response.status_code == 303

    second_response = checkout_web.post("/cart/checkout", data={"checkout_token": token})
    assert second_response.status_code == 303
    assert second_response.location == first_response.location
    assert db_session.query(Order).count() == 1

    add_row(db_session, buyer, later)
    replay = checkout_web.post("/cart/checkout", data={"checkout_token": token})
    assert replay.status_code == 303 and replay.location == first_response.location
    assert db_session.query(Order).count() == 1
    assert later.status == "active"
    assert db_session.query(CartItem).filter_by(user_id=buyer.id,
                                                product_id=later.id).count() == 1


def test_expired_unused_token_conflicts_but_completed_token_still_recovers(
        checkout_web, db_app, user_factory, product_factory, db_session):
    Order, _ = order_models()
    buyer = user_factory()
    product = product_factory()
    add_row(db_session, buyer, product)
    sign_in(checkout_web, buyer)
    page = checkout_web.get("/cart")
    token = form_value(page, "checkout_token")
    db_app.config["CHECKOUT_TOKEN_MAX_AGE"] = -1
    expired = checkout_web.post("/cart/checkout", data={"checkout_token": token})
    assert expired.status_code == 409 and db_session.query(Order).count() == 0

    db_app.config["CHECKOUT_TOKEN_MAX_AGE"] = 1800
    fresh_page = checkout_web.get("/cart")
    completed, completed_token = checkout(checkout_web, fresh_page)
    assert completed.status_code == 303
    db_app.config["CHECKOUT_TOKEN_MAX_AGE"] = -1
    recovered = checkout_web.post("/cart/checkout",
                                  data={"checkout_token": completed_token})
    assert recovered.status_code == 303
    assert recovered.location == completed.location
    assert db_session.query(Order).count() == 1


def test_bad_repeated_and_wrong_owner_tokens_do_not_mutate(checkout_web, user_factory,
                                                           product_factory, db_session):
    from app.models import CartItem
    Order, _ = order_models()
    buyer, other = user_factory(), user_factory()
    product = product_factory()
    add_row(db_session, buyer, product)
    sign_in(checkout_web, buyer)
    token = form_value(checkout_web.get("/cart"), "checkout_token")

    assert checkout_web.post("/cart/checkout",
        data={"checkout_token": [token, token]}).status_code == 400
    assert checkout_web.post("/cart/checkout",
        data={"checkout_token": token + "tampered"}).status_code == 400
    sign_in(checkout_web, other)
    assert checkout_web.post("/cart/checkout",
        data={"checkout_token": token}).status_code == 400
    assert db_session.query(Order).count() == 0
    assert db_session.query(CartItem).count() == 1 and product.status == "active"


def test_success_page_is_private_and_refresh_is_read_only(checkout_web, user_factory,
                                                          product_factory, db_session):
    Order, _ = order_models()
    buyer, stranger = user_factory(), user_factory()
    product = product_factory(title="Receipt privacy product")
    add_row(db_session, buyer, product)
    sign_in(checkout_web, buyer)
    response, _ = checkout(checkout_web)
    order_id = db_session.query(Order).one().id
    first = checkout_web.get(response.location)
    second = checkout_web.get(response.location)
    assert first.status_code == second.status_code == 200
    assert db_session.query(Order).count() == 1
    sign_in(checkout_web, stranger)
    denied = checkout_web.get(f"/orders/{order_id}/success")
    assert denied.status_code == 404
    assert b"Receipt privacy product" not in denied.data


def test_real_csrf_is_required_for_checkout(db_app, user_factory, product_factory, db_session):
    Order, _ = order_models()
    buyer, product = user_factory(), product_factory()
    add_row(db_session, buyer, product)
    client = db_app.test_client()
    sign_in(client, buyer)
    page = client.get("/cart")
    checkout_value = form_value(page, "checkout_token")
    assert client.post("/cart/checkout",
                       data={"checkout_token": checkout_value}).status_code == 400
    csrf_value = csrf_for(page.get_data(as_text=True), "/cart/checkout")
    response = client.post("/cart/checkout", data={
        "checkout_token": checkout_value, "csrf_token": csrf_value})
    assert response.status_code == 303 and db_session.query(Order).count() == 1


def test_commit_failure_rolls_back_order_status_and_cart(checkout_web, user_factory,
                                                         product_factory, db_session,
                                                         monkeypatch):
    from app.models import CartItem
    Order, OrderItem = order_models()
    buyer, product = user_factory(), product_factory()
    original_version = product.version
    add_row(db_session, buyer, product)
    sign_in(checkout_web, buyer)
    page = checkout_web.get("/cart")
    token = form_value(page, "checkout_token")

    with monkeypatch.context() as patch:
        def fail_commit():
            raise OperationalError("private-checkout-path", {},
                                   Exception("private-checkout-canary"))
        patch.setattr(db_session, "commit", fail_commit)
        response = checkout_web.post("/cart/checkout", data={"checkout_token": token})

    assert response.status_code == 503
    assert b"private-checkout-canary" not in response.data
    assert db_session.query(Order).count() == 0
    assert db_session.query(OrderItem).count() == 0
    db_session.refresh(product)
    assert product.status == "active" and product.version == original_version
    assert db_session.query(CartItem).filter_by(user_id=buyer.id).count() == 1


def test_two_buyers_racing_for_one_product_create_at_most_one_order(
        db_app, user_factory, product_factory, db_session):
    from app.models import CartItem, Product
    Order, OrderItem = order_models()
    db_app.config.update(WTF_CSRF_ENABLED=False,
                         SECRET_KEY="isolated-mm025-race-secret",
                         CHECKOUT_TOKEN_MAX_AGE=1800)
    first_buyer, second_buyer = user_factory(), user_factory()
    product = product_factory()
    add_row(db_session, first_buyer, product)
    add_row(db_session, second_buyer, product)
    clients = [db_app.test_client(), db_app.test_client()]
    for client, buyer in zip(clients, (first_buyer, second_buyer)):
        sign_in(client, buyer)
    tokens = [form_value(client.get("/cart"), "checkout_token") for client in clients]
    product_id = product.id
    db_session.remove()

    def submit(pair):
        client, token = pair
        return client.post("/cart/checkout", data={"checkout_token": token}).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(submit, zip(clients, tokens)))

    assert sorted(statuses) == [303, 409]
    assert db_session.query(Order).count() == 1
    assert db_session.query(OrderItem).count() == 1
    assert db_session.query(CartItem).count() == 1
    assert db_session.get(Product, product_id).status == "sold"


def test_two_overlapping_posts_with_same_token_return_the_same_order(
        db_app, user_factory, product_factory, db_session):
    from app.models import CartItem
    Order, OrderItem = order_models()
    db_app.config.update(WTF_CSRF_ENABLED=False,
                         SECRET_KEY="isolated-mm025-same-token-secret",
                         CHECKOUT_TOKEN_MAX_AGE=1800)
    buyer, product = user_factory(), product_factory()
    add_row(db_session, buyer, product)
    clients = [db_app.test_client(), db_app.test_client()]
    for client in clients:
        sign_in(client, buyer)
    token = form_value(clients[0].get("/cart"), "checkout_token")
    db_session.remove()

    def submit(client):
        response = client.post("/cart/checkout", data={"checkout_token": token})
        return response.status_code, response.location

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(submit, clients))

    assert [response[0] for response in responses] == [303, 303]
    assert len({response[1] for response in responses}) == 1
    assert db_session.query(Order).count() == 1
    assert db_session.query(OrderItem).count() == 1
    assert db_session.query(CartItem).count() == 0

