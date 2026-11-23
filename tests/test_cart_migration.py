"""MM-019 migration contract, written before the cart revision exists."""

import sqlite3

from tests.test_migrations import make_migration_app, table_names


def test_cart_migration_upgrade_schema_constraints_and_downgrade(tmp_path):
    application, database_path = make_migration_app(tmp_path, "cart-migration.sqlite")
    runner = application.test_cli_runner()
    upgrade = runner.invoke(args=["db", "upgrade"])
    assert upgrade.exit_code == 0, upgrade.output
    assert "cart_items" in table_names(database_path)

    with sqlite3.connect(database_path) as connection:
        columns = connection.execute("PRAGMA table_info(cart_items)").fetchall()
        foreign_keys = connection.execute("PRAGMA foreign_key_list(cart_items)").fetchall()
        indexes = connection.execute("PRAGMA index_list(cart_items)").fetchall()
        assert {row[1] for row in columns} == {"user_id", "product_id", "added_at"}
        assert [row[1] for row in columns if row[5]] == ["user_id", "product_id"]
        assert {(row[2], row[3]) for row in foreign_keys} == {
            ("users", "user_id"), ("products", "product_id")}
        assert all(row[6].upper() == "RESTRICT" for row in foreign_keys)
        assert any("product" in row[1] for row in indexes)

        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("INSERT INTO users "
            "(id,username,email,password_hash,enabled,personalization,created_at,updated_at) "
            "VALUES (1,'cart-seller','seller@cart.test','hash',1,0,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),"
            "(2,'cart-buyer','buyer@cart.test','hash',1,0,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)")
        connection.execute("INSERT INTO products "
            "(id,version,seller_id,title,description,price,currency,category,condition,status,created_at,updated_at) "
            "VALUES (1,1,1,'Cart product','Description long enough',1000,'USD','other','good','active',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)")
        connection.execute("INSERT INTO cart_items (user_id,product_id,added_at) "
                           "VALUES (2,1,CURRENT_TIMESTAMP)")
        try:
            connection.execute("INSERT INTO cart_items (user_id,product_id,added_at) "
                               "VALUES (2,1,CURRENT_TIMESTAMP)")
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("Duplicate cart pair was accepted")

    downgrade = runner.invoke(args=["db", "downgrade", "d88e8d30439f"])
    assert downgrade.exit_code == 0, downgrade.output
    remaining = table_names(database_path)
    assert "cart_items" not in remaining
    assert {"users", "products", "saved_products"} <= remaining


def test_cart_migration_preserves_existing_marketplace_rows(tmp_path):
    application, database_path = make_migration_app(tmp_path, "cart-existing.sqlite")
    runner = application.test_cli_runner()
    assert runner.invoke(args=["db", "upgrade", "d88e8d30439f"]).exit_code == 0
    with sqlite3.connect(database_path) as connection:
        connection.execute("INSERT INTO users "
            "(id,username,email,password_hash,enabled,personalization,created_at,updated_at) "
            "VALUES (1,'existing-cart','existing@cart.test','hash',1,0,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)")
        connection.execute("INSERT INTO products "
            "(id,version,seller_id,title,description,price,currency,category,condition,status,created_at,updated_at) "
            "VALUES (1,1,1,'Existing cart item','Description long enough',1299,'USD','other','good','active',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)")
        connection.commit()
    result = runner.invoke(args=["db", "upgrade"])
    assert result.exit_code == 0, result.output
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT username FROM users").fetchone() == ("existing-cart",)
        assert connection.execute("SELECT title,price FROM products").fetchone() == ("Existing cart item", 1299)
        assert connection.execute("SELECT count(*) FROM cart_items").fetchone() == (0,)

