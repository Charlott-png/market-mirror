"""MM-002 tests proving Alembic migrations create the approved schema."""

import sqlite3
from decimal import Decimal

import pytest


def make_migration_app(tmp_path, name="migration-test.sqlite"):
    """Create an app pointing at an empty database without calling create_all."""
    from app import create_app

    database_path = tmp_path / name
    application = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path.as_posix()}",
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        }
    )
    return application, database_path


def table_names(database_path):
    """Return non-Alembic application table names from a SQLite file."""
    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
    return {row[0] for row in rows}


def test_empty_database_upgrades_to_approved_schema(tmp_path):
    """TEST-MIG-001 / AC-DB-001: migrations create tables and constraints."""
    application, database_path = make_migration_app(tmp_path)
    result = application.test_cli_runner().invoke(args=["db", "upgrade"])

    assert result.exit_code == 0, result.output
    assert {"alembic_version", "users", "products"} <= table_names(database_path)

    with sqlite3.connect(database_path) as connection:
        user_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(users)").fetchall()
        }
        product_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(products)").fetchall()
        }
        foreign_keys = connection.execute("PRAGMA foreign_key_list(products)").fetchall()
        product_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='products'"
        ).fetchone()[0]

    assert {
        "id",
        "username",
        "email",
        "password_hash",
        "bio",
        "created_at",
        "updated_at",
    } <= user_columns
    assert {
        "id",
        "seller_id",
        "title",
        "description",
        "price",
        "currency",
        "category",
        "condition",
        "status",
        "image_filename",
        "created_at",
        "updated_at",
    } <= product_columns
    assert any(row[2] == "users" and row[3] == "seller_id" for row in foreign_keys)
    assert "CHECK" in product_sql.upper()


def test_repeated_migration_upgrade_is_safe(tmp_path):
    """TEST-MIG-002: applying the latest migration twice is idempotent."""
    application, database_path = make_migration_app(tmp_path)
    runner = application.test_cli_runner()

    first = runner.invoke(args=["db", "upgrade"])
    first_tables = table_names(database_path)
    second = runner.invoke(args=["db", "upgrade"])

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    assert table_names(database_path) == first_tables


def test_migration_downgrade_and_reupgrade(tmp_path):
    """TEST-MIG-003 / AC-DB-010: disposable schema can move down and up."""
    application, database_path = make_migration_app(tmp_path)
    runner = application.test_cli_runner()

    upgrade = runner.invoke(args=["db", "upgrade"])
    downgrade = runner.invoke(args=["db", "downgrade", "base"])
    tables_after_downgrade = table_names(database_path)
    reupgrade = runner.invoke(args=["db", "upgrade"])

    assert upgrade.exit_code == 0, upgrade.output
    assert downgrade.exit_code == 0, downgrade.output
    assert "users" not in tables_after_downgrade
    assert "products" not in tables_after_downgrade
    assert reupgrade.exit_code == 0, reupgrade.output
    assert {"users", "products"} <= table_names(database_path)


def test_migrated_database_accepts_maximum_price_and_rejects_bad_raw_prices(tmp_path):
    """Migration constraints must agree with model constraints, including cents."""
    from app.extensions import db
    from app.models import Product
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    application, database_path = make_migration_app(tmp_path)
    runner = application.test_cli_runner()
    assert runner.invoke(args=["db", "upgrade"]).exit_code == 0
    assert runner.invoke(args=["seed"]).exit_code == 0
    with application.app_context():
        product = db.session.scalars(db.select(Product)).first()
        product.price = Decimal("9999999.99")
        db.session.commit()
        for invalid in (-1, 0, 1.5, 1000000000):
            with pytest.raises(IntegrityError):
                db.session.execute(text("UPDATE products SET price = :price WHERE id = :id"),
                                   {"price": invalid, "id": product.id})
                db.session.commit()
            db.session.rollback()
        assert product.price == Decimal("9999999.99")
        db.session.remove()
        db.engine.dispose()


def test_new_app_persists_data_while_separate_test_database_changes(tmp_path):
    """AC-DB-009: a second application/database cannot erase existing data."""
    from app.extensions import db
    from app.models import Product, User

    first_app, first_path = make_migration_app(tmp_path, "existing.sqlite")
    runner = first_app.test_cli_runner()
    assert runner.invoke(args=["db", "upgrade"]).exit_code == 0
    assert runner.invoke(args=["seed"]).exit_code == 0
    with first_app.app_context():
        db.session.remove()
        db.engine.dispose()
    before = first_path.read_bytes()

    other_app, _ = make_migration_app(tmp_path, "isolated.sqlite")
    with other_app.app_context():
        db.create_all()
        db.session.add(User(username="isolated", email="isolated@example.test", password_hash="test-only-hash"))
        db.session.commit()
        db.drop_all()
        db.session.remove()
        db.engine.dispose()
    assert first_path.read_bytes() == before

    reopened, _ = make_migration_app(tmp_path, "existing.sqlite")
    with reopened.app_context():
        assert db.session.query(User).count() == 3
        assert db.session.query(Product).count() == 12
        db.session.remove()
        db.engine.dispose()


def test_marketplace_upgrade_preserves_existing_foundation_rows(tmp_path):
    application, database_path = make_migration_app(tmp_path, "upgrade-populated.sqlite")
    runner = application.test_cli_runner()
    first = runner.invoke(args=["db", "upgrade", "46b4b94079af"])
    assert first.exit_code == 0, first.output
    with sqlite3.connect(database_path) as connection:
        connection.execute("INSERT INTO users (id,username,email,password_hash,created_at,updated_at) "
                           "VALUES (1,'existing','existing@example.test','test-only-hash',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)")
        connection.execute("INSERT INTO products (seller_id,title,description,price,currency,category,condition,status,created_at,updated_at) "
                           "VALUES (1,'Existing listing','Existing description long enough',1999,'USD','other','good','active',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)")
    result = runner.invoke(args=["db", "upgrade"])
    assert result.exit_code == 0, result.output
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT title,price,version FROM products").fetchone() == ("Existing listing",1999,1)
        assert connection.execute("SELECT username,enabled,personalization FROM users").fetchone() == ("existing",1,0)
