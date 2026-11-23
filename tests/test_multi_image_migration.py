"""MM-026 product-gallery migration contracts written before implementation."""

import sqlite3

from tests.test_migrations import make_migration_app, table_names


def test_multi_image_migration_creates_table_constraints_and_backfills(tmp_path):
    application, database_path = make_migration_app(tmp_path, "mm026-backfill.sqlite")
    runner = application.test_cli_runner()
    first = runner.invoke(args=["db", "upgrade", "a25c0de02501"])
    assert first.exit_code == 0, first.output
    cover = "1" * 32 + ".jpg"
    with sqlite3.connect(database_path) as connection:
        connection.execute("INSERT INTO users "
            "(id,username,email,password_hash,enabled,personalization,created_at,updated_at) "
            "VALUES (1,'gallery-owner','owner@gallery.test','hash',1,0,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)")
        connection.execute("INSERT INTO products "
            "(id,version,seller_id,title,description,price,currency,category,condition,status,image_filename,created_at,updated_at) "
            "VALUES (1,1,1,'Existing gallery product','Description long enough',2500,'USD','other','good','active',?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)",
            (cover,))
        connection.commit()
    upgrade = runner.invoke(args=["db", "upgrade"])
    assert upgrade.exit_code == 0, upgrade.output
    assert "product_images" in table_names(database_path)
    with sqlite3.connect(database_path) as connection:
        columns = {row[1] for row in connection.execute(
            "PRAGMA table_info(product_images)").fetchall()}
        fks = connection.execute("PRAGMA foreign_key_list(product_images)").fetchall()
        indexes = connection.execute("PRAGMA index_list(product_images)").fetchall()
        sql = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' "
                                 "AND name='product_images'").fetchone()[0]
        row = connection.execute("SELECT product_id,filename,position FROM product_images").fetchone()
        product = connection.execute("SELECT image_filename,version FROM products").fetchone()
    assert columns == {"id", "product_id", "filename", "position", "created_at"}
    assert row == (1, cover, 0) and product == (cover, 1)
    assert any(item[2] == "products" and item[3] == "product_id" and
               item[6].upper() == "CASCADE" for item in fks)
    assert any(item[2] for item in indexes)
    assert "CHECK" in sql.upper()


def test_multi_image_migration_downgrade_preserves_cover_and_old_tables(tmp_path):
    application, database_path = make_migration_app(tmp_path, "mm026-down.sqlite")
    runner = application.test_cli_runner()
    assert runner.invoke(args=["db", "upgrade"]).exit_code == 0
    downgrade = runner.invoke(args=["db", "downgrade", "a25c0de02501"])
    assert downgrade.exit_code == 0, downgrade.output
    names = table_names(database_path)
    assert "product_images" not in names
    assert {"products", "cart_items", "orders", "order_items"} <= names


def test_multi_image_migration_rejects_ambiguous_legacy_cover(tmp_path):
    application, database_path = make_migration_app(tmp_path, "mm026-duplicate.sqlite")
    runner = application.test_cli_runner()
    assert runner.invoke(args=["db", "upgrade", "a25c0de02501"]).exit_code == 0
    duplicate = "2" * 32 + ".jpg"
    with sqlite3.connect(database_path) as connection:
        connection.execute("INSERT INTO users "
            "(id,username,email,password_hash,enabled,personalization,created_at,updated_at) VALUES "
            "(1,'first-owner','first@gallery.test','hash',1,0,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),"
            "(2,'second-owner','second@gallery.test','hash',1,0,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)")
        for identifier in (1, 2):
            connection.execute("INSERT INTO products "
                "(id,version,seller_id,title,description,price,currency,category,condition,status,image_filename,created_at,updated_at) "
                "VALUES (?,1,?,'Duplicate cover item','Description long enough',1000,'USD','other','good','active',?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)",
                (identifier, identifier, duplicate))
        connection.commit()
    result = runner.invoke(args=["db", "upgrade"])
    assert result.exit_code != 0
    with sqlite3.connect(database_path) as connection:
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        product_count = connection.execute("SELECT count(*) FROM products").fetchone()[0]
    assert revision == "a25c0de02501" and product_count == 2

