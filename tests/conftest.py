"""Shared pytest fixtures for the Market Mirror test suite.

A fixture prepares something a test needs. These fixtures will create a fresh
Flask application and a test client after the application is implemented.
"""

import pytest


@pytest.fixture()
def app(tmp_path):
    """Create a Market Mirror application configured for safe testing."""
    from app import create_app

    database_path = tmp_path / "market-mirror-test.sqlite"
    application = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path.as_posix()}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "UPLOAD_FOLDER": str(tmp_path / "uploads"),
            "AI_FOLDER": str(tmp_path / "ai"),
        }
    )
    yield application
    from app.extensions import db
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


@pytest.fixture()
def client(app):
    """Act like a small browser without starting a real network server."""
    return app.test_client()


@pytest.fixture()
def db_app(app):
    """Create and later remove tables in the test-owned temporary database."""
    # The import stays inside the fixture so pytest can collect the complete
    # MM-002 suite before the database extension exists during the Red stage.
    from app.extensions import db

    with app.app_context():
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def db_session(db_app):
    """Provide the current isolated SQLAlchemy session."""
    from app.extensions import db

    with db_app.app_context():
        yield db.session
        db.session.rollback()
        db.session.remove()


@pytest.fixture()
def user_factory(db_session):
    """Create valid users while allowing a test to override selected fields."""
    counter = {"value": 0}

    def create_user(**overrides):
        from app.models import User

        counter["value"] += 1
        number = counter["value"]
        values = {
            "username": f"student-{number}",
            "email": f"student-{number}@example.test",
            "password_hash": f"secure-test-hash-{number}",
        }
        values.update(overrides)
        user = User(**values)
        db_session.add(user)
        db_session.commit()
        return user

    return create_user


@pytest.fixture()
def product_factory(db_session, user_factory):
    """Create valid products with an explicit or automatically created seller."""
    from decimal import Decimal

    counter = {"value": 0}

    def create_product(seller=None, **overrides):
        from app.models import Product

        counter["value"] += 1
        number = counter["value"]
        owner = seller or user_factory()
        values = {
            "seller": owner,
            "title": f"Test product {number}",
            "description": "A complete product description for database testing.",
            "price": Decimal("49.99"),
            "currency": "USD",
            "category": "electronics",
            "condition": "good",
            "status": "active",
        }
        values.update(overrides)
        product = Product(**values)
        db_session.add(product)
        db_session.commit()
        return product

    return create_product
