"""MM-002 tests for database configuration and isolation."""

from pathlib import Path


def test_development_database_defaults_to_instance_directory(monkeypatch):
    """TEST-DB-001: Normal development uses an ignored instance database."""
    from app import create_app

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("SECRET_KEY", "test-configuration-secret-32-characters")

    application = create_app()
    database_uri = application.config["SQLALCHEMY_DATABASE_URI"]

    assert database_uri.startswith("sqlite:///")
    assert "instance" in database_uri.lower()
    assert database_uri.lower().endswith((".sqlite", ".db"))


def test_test_database_is_temporary_and_separate(app, tmp_path):
    """TEST-DB-002: pytest never points at the development database."""
    database_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    database_path = database_uri.removeprefix("sqlite:///")

    assert app.config["TESTING"] is True
    assert Path(database_path).parent == tmp_path
    assert "instance" not in database_path.lower()


def test_sqlite_foreign_keys_are_enabled(db_app):
    """TEST-DB-003: SQLite enforces product-to-seller foreign keys."""
    from app.extensions import db

    with db_app.app_context():
        enabled = db.session.execute(db.text("PRAGMA foreign_keys")).scalar()

    assert enabled == 1


def test_starting_application_does_not_seed_rows(db_app):
    """TEST-DB-004 / AC-DB-012: Startup never creates demo data."""
    from app.extensions import db
    from app.models import Product, User

    with db_app.app_context():
        assert db.session.query(User).count() == 0
        assert db.session.query(Product).count() == 0
