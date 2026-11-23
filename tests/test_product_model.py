"""MM-002 tests for Product data, relationships, and constraints."""

from datetime import timedelta
from decimal import Decimal

import pytest


def test_products_persist_through_both_relationship_directions(
    db_app, user_factory, product_factory
):
    """TEST-PRODUCT-001 / AC-DB-002: seller relationship works both ways."""
    from app.extensions import db
    from app.models import Product, User

    seller = user_factory(username="seller", email="seller@example.test")
    first = product_factory(seller=seller, title="First product")
    second = product_factory(seller=seller, title="Second product")
    seller_id = seller.id
    product_ids = {first.id, second.id}

    db.session.remove()
    stored_seller = db.session.get(User, seller_id)
    stored_products = db.session.query(Product).filter_by(seller_id=seller_id).all()

    assert {product.id for product in stored_seller.products} == product_ids
    assert {product.id for product in stored_products} == product_ids
    assert all(product.seller.id == seller_id for product in stored_products)


@pytest.mark.parametrize("seller_value", [None, 999999])
def test_product_requires_an_existing_seller(db_session, seller_value):
    """TEST-PRODUCT-002 / AC-DB-003: ownerless products never persist."""
    from app.models import Product
    from sqlalchemy.exc import IntegrityError

    product = Product(
        seller_id=seller_value,
        title="Ownerless product",
        description="This attempted product must not be committed.",
        price=Decimal("10.00"),
        currency="USD",
        category="other",
        condition="good",
        status="active",
    )
    db_session.add(product)

    with pytest.raises((IntegrityError, ValueError, TypeError)):
        db_session.commit()

    db_session.rollback()
    assert db_session.query(Product).count() == 0


def test_price_round_trip_is_exact(db_app, product_factory):
    """TEST-PRODUCT-003 / AC-DB-005: decimal 10.10 remains exact."""
    from app.extensions import db
    from app.models import Product

    product = product_factory(price=Decimal("10.10"))
    product_id = product.id
    db.session.remove()

    stored = db.session.get(Product, product_id)
    assert stored.price == Decimal("10.10")
    assert not isinstance(stored.price, float)


@pytest.mark.parametrize(
    ("price", "is_valid"),
    [
        (Decimal("-0.01"), False),
        (Decimal("0.00"), False),
        (Decimal("0.01"), True),
        (Decimal("9999999.99"), True),
        (Decimal("10000000.00"), False),
        (Decimal("1.001"), False),
        ("not-a-price", False),
        (1.25, False),
        (Decimal("NaN"), False),
        (Decimal("Infinity"), False),
    ],
)
def test_price_boundaries(db_session, user_factory, price, is_valid):
    """TEST-PRODUCT-004: only finite two-decimal in-range prices persist."""
    from app.models import Product

    seller = user_factory()
    values = {
        "seller": seller,
        "title": "Boundary price product",
        "description": "A sufficiently long product description.",
        "price": price,
        "currency": "USD",
        "category": "other",
        "condition": "good",
        "status": "active",
    }

    if is_valid:
        product = Product(**values)
        db_session.add(product)
        db_session.commit()
        assert product.id is not None
    else:
        with pytest.raises((ValueError, TypeError, ArithmeticError)):
            Product(**values)
        db_session.rollback()


@pytest.mark.parametrize(
    ("field", "valid_values", "invalid_values"),
    [
        ("currency", ["USD"], ["", "usd", "EUR"]),
        (
            "category",
            [
                "electronics",
                "home_garden",
                "clothing",
                "books_media",
                "sports_outdoors",
                "toys_games",
                "other",
            ],
            ["", "Electronics", "unknown"],
        ),
        ("condition", ["new", "like_new", "good", "fair"], ["", "Good", "poor"]),
        ("status", ["active", "sold", "archived"], ["", "Active", "deleted"]),
    ],
)
def test_choice_fields_enforce_allow_lists(
    db_session, user_factory, field, valid_values, invalid_values
):
    """TEST-PRODUCT-005 / AC-DB-006: stored choice keys are controlled."""
    from app.models import Product

    seller = user_factory()
    base_values = {
        "seller": seller,
        "title": "Choice test product",
        "description": "A sufficiently long product description.",
        "price": Decimal("25.00"),
        "currency": "USD",
        "category": "other",
        "condition": "good",
        "status": "active",
    }

    for value in valid_values:
        values = dict(base_values)
        values[field] = value
        product = Product(**values)
        db_session.add(product)
        db_session.flush()
        db_session.expunge(product)

    db_session.rollback()

    for value in invalid_values:
        values = dict(base_values)
        values[field] = value
        with pytest.raises((ValueError, TypeError)):
            Product(**values)


@pytest.mark.parametrize(
    ("field", "value", "is_valid"),
    [
        ("title", "ab", False),
        ("title", "abc", True),
        ("title", "t" * 120, True),
        ("title", "t" * 121, False),
        ("title", "   ", False),
        ("description", "d" * 9, False),
        ("description", "d" * 10, True),
        ("description", "d" * 5000, True),
        ("description", "d" * 5001, False),
        ("description", "   ", False),
        ("image_filename", "i" * 255, True),
        ("image_filename", "i" * 256, False),
    ],
)
def test_product_text_boundaries(
    db_session, user_factory, field, value, is_valid
):
    """TEST-PRODUCT-006: listing text follows approved length rules."""
    from app.models import Product

    values = {
        "seller": user_factory(),
        "title": "Valid product title",
        "description": "A sufficiently long product description.",
        "price": Decimal("20.00"),
        "currency": "USD",
        "category": "other",
        "condition": "good",
        "status": "active",
    }
    values[field] = value

    if is_valid:
        product = Product(**values)
        db_session.add(product)
        db_session.commit()
        assert product.id is not None
    else:
        with pytest.raises((ValueError, TypeError)):
            Product(**values)
        db_session.rollback()


def test_product_representation_hides_full_description(product_factory):
    """TEST-PRODUCT-007: debugging text remains short and non-private."""
    description_canary = "private-description-canary-" + ("x" * 100)
    product = product_factory(
        title="A product with a useful title",
        description=description_canary,
    )

    representation = repr(product)

    assert str(product.id) in representation
    assert "A product with a useful title" in representation
    assert description_canary not in representation


def test_product_timestamps_use_utc_and_update_safely(db_app, product_factory):
    """TEST-PRODUCT-008: creation time is stable and update time advances."""
    from app.extensions import db
    from app.models import Product

    product = product_factory()
    product_id = product.id
    created_at = product.created_at
    first_updated_at = product.updated_at

    assert created_at.utcoffset() == timedelta(0)
    assert first_updated_at.utcoffset() == timedelta(0)

    product.title = "Updated valid title"
    db.session.commit()
    db.session.refresh(product)

    assert product.created_at == created_at
    assert product.updated_at >= first_updated_at

    committed_updated_at = product.updated_at
    with pytest.raises(ValueError):
        product.status = "not-a-status"
    db.session.rollback()
    db.session.refresh(product)
    assert product.updated_at == committed_updated_at
    assert db.session.get(Product, product_id) is not None


def test_user_deletion_with_products_is_restricted(
    db_session, user_factory, product_factory
):
    """TEST-PRODUCT-009 / AC-DB-007: seller deletion cannot orphan products."""
    from app.models import Product, User
    from sqlalchemy.exc import IntegrityError

    seller = user_factory()
    product = product_factory(seller=seller)
    seller_id = seller.id
    product_id = product.id

    db_session.delete(seller)
    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()
    assert db_session.get(User, seller_id) is not None
    assert db_session.get(Product, product_id) is not None
