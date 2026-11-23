"""Additional MM-002 integrity checks that bypass model validators."""

from decimal import Decimal

import pytest


@pytest.mark.parametrize("field,value", [
    ("category", "unsupported"), ("condition", "broken"),
    ("status", "deleted"), ("currency", "EUR"), ("seller_id", 999999),
    ("title", ""), ("description", "short"),
])
def test_database_rejects_invalid_direct_product_updates(
    db_session, product_factory, field, value
):
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    product = product_factory()
    original = getattr(product, field)
    # field comes only from the fixed test matrix, never from user input.
    with pytest.raises(IntegrityError):
        db_session.execute(text(f"UPDATE products SET {field} = :value WHERE id = :id"),
                           {"value": value, "id": product.id})
        db_session.commit()
    db_session.rollback()
    db_session.refresh(product)
    assert getattr(product, field) == original


@pytest.mark.parametrize("field,value", [
    ("username", "UPPERCASE"), ("email", "UPPER@EXAMPLE.TEST"),
    ("username", " x "), ("password_hash", ""),
])
def test_database_rejects_noncanonical_identity(db_session, user_factory, field, value):
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    user = user_factory()
    with pytest.raises(IntegrityError):
        db_session.execute(text(f"UPDATE users SET {field} = :value WHERE id = :id"),
                           {"value": value, "id": user.id})
        db_session.commit()
    db_session.rollback()
    assert db_session.get(type(user), user.id) is not None


def test_prices_remain_exact_across_many_cent_values(db_session, product_factory):
    from sqlalchemy import text

    product = product_factory()
    for cents in (1, 7, 29, 1010, 999999999):
        product.price = Decimal(cents) / 100
        db_session.commit()
        db_session.refresh(product)
        assert product.price == Decimal(cents) / 100
        # SQLite's physical value must not rely on binary floating point.
        storage = db_session.execute(text(
            "SELECT typeof(price) FROM products WHERE id = :id"
        ), {"id": product.id}).scalar_one()
        assert storage == "integer"


def test_seed_collision_fails_without_modifying_existing_data(db_app, user_factory):
    from app.extensions import db
    from app.models import Product, User

    user = user_factory(username="demo-alex", email="real-owner@example.test")
    user_id = user.id
    result = db_app.test_cli_runner().invoke(args=["seed"])
    assert result.exit_code != 0
    with db_app.app_context():
        assert db.session.query(User).count() == 1
        assert db.session.query(Product).count() == 0
        assert db.session.get(User, user_id).email == "real-owner@example.test"


def test_seed_refuses_production(db_app):
    from app.extensions import db
    from app.models import User

    db_app.config["APP_ENV"] = "production"
    result = db_app.test_cli_runner().invoke(args=["seed"])
    assert result.exit_code != 0
    with db_app.app_context():
        assert db.session.query(User).count() == 0


def test_test_mode_without_url_ignores_environment_database(monkeypatch):
    from app import create_app

    monkeypatch.setenv("DATABASE_URL", "sqlite:///must-not-use.sqlite")
    application = create_app({"TESTING": True})
    assert application.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"
