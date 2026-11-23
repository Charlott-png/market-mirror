"""MM-028 migration contracts, written before the migration implementation."""

import sqlite3

from tests.test_migrations import make_migration_app, table_names


PRIOR_REVISION = "b26c0de02601"
MM028_REVISION = "c28d0de02801"


def seed_prior_schema(application, database_path):
    runner = application.test_cli_runner()
    result = runner.invoke(args=["db", "upgrade", PRIOR_REVISION])
    assert result.exit_code == 0, result.output
    with sqlite3.connect(database_path) as connection:
        connection.execute("""INSERT INTO users
            (id,username,email,password_hash,enabled,personalization,created_at,updated_at)
            VALUES (1,'history-user','history@example.test','hash',1,0,
                    CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)""")
        connection.execute("""INSERT INTO products
            (id,version,seller_id,title,description,price,currency,category,
             condition,status,image_filename,created_at,updated_at)
            VALUES (1,1,1,'Existing product','Description long enough',2500,
                    'USD','electronics','good','active',NULL,
                    CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)""")
        connection.commit()
    return runner


def test_mm028_upgrade_creates_exact_history_schema_and_preserves_rows(tmp_path):
    application, database_path = make_migration_app(tmp_path, "mm028-up.sqlite")
    runner = seed_prior_schema(application, database_path)

    result = runner.invoke(args=["db", "upgrade"])
    assert result.exit_code == 0, result.output
    assert "recent_product_views" in table_names(database_path)
    with sqlite3.connect(database_path) as connection:
        columns = connection.execute(
            "PRAGMA table_info(recent_product_views)").fetchall()
        foreign_keys = connection.execute(
            "PRAGMA foreign_key_list(recent_product_views)").fetchall()
        indexes = connection.execute(
            "PRAGMA index_list(recent_product_views)").fetchall()
        revision = connection.execute(
            "SELECT version_num FROM alembic_version").fetchone()[0]
        counts = (connection.execute("SELECT count(*) FROM users").fetchone()[0],
                  connection.execute("SELECT count(*) FROM products").fetchone()[0],
                  connection.execute("SELECT count(*) FROM recent_product_views").fetchone()[0])
    assert {row[1] for row in columns} == {"user_id", "product_id", "viewed_at"}
    assert {row[1] for row in columns if row[5]} == {"user_id", "product_id"}
    assert len(foreign_keys) == 2
    assert any(row[1] == "ix_recent_product_views_user_viewed_at"
               for row in indexes)
    assert revision == MM028_REVISION
    assert counts == (1, 1, 0)


def test_mm028_database_rejects_duplicate_and_invalid_history_rows(tmp_path):
    application, database_path = make_migration_app(tmp_path, "mm028-constraints.sqlite")
    runner = seed_prior_schema(application, database_path)
    assert runner.invoke(args=["db", "upgrade"]).exit_code == 0
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("""INSERT INTO recent_product_views
            (user_id,product_id,viewed_at) VALUES (1,1,CURRENT_TIMESTAMP)""")
        connection.commit()
        for values in ((1, 1), (999, 1), (1, 999)):
            try:
                connection.execute("""INSERT INTO recent_product_views
                    (user_id,product_id,viewed_at)
                    VALUES (?,?,CURRENT_TIMESTAMP)""", values)
                connection.commit()
            except sqlite3.IntegrityError:
                connection.rollback()
            else:
                raise AssertionError(f"Invalid history row was accepted: {values}")
        assert connection.execute(
            "SELECT user_id,product_id FROM recent_product_views").fetchall() == [(1, 1)]


def test_mm028_downgrade_removes_only_history_table_and_reupgrades(tmp_path):
    application, database_path = make_migration_app(tmp_path, "mm028-down.sqlite")
    runner = seed_prior_schema(application, database_path)
    assert runner.invoke(args=["db", "upgrade"]).exit_code == 0
    downgrade = runner.invoke(args=["db", "downgrade", PRIOR_REVISION])
    assert downgrade.exit_code == 0, downgrade.output
    names = table_names(database_path)
    assert "recent_product_views" not in names
    assert {"users", "products", "product_images", "orders"} <= names
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT count(*) FROM users").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM products").fetchone()[0] == 1
    reupgrade = runner.invoke(args=["db", "upgrade"])
    assert reupgrade.exit_code == 0, reupgrade.output
    assert "recent_product_views" in table_names(database_path)

