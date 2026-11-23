"""MM-025 Alembic contracts, written before the order revision exists."""

import sqlite3

from tests.test_migrations import make_migration_app, table_names


def test_order_migration_creates_expected_schema_and_constraints(tmp_path):
    application, database_path = make_migration_app(tmp_path, "mm025-schema.sqlite")
    runner = application.test_cli_runner()
    result = runner.invoke(args=["db", "upgrade"])
    assert result.exit_code == 0, result.output
    assert {"orders", "order_items"} <= table_names(database_path)

    with sqlite3.connect(database_path) as connection:
        order_columns = {row[1] for row in connection.execute(
            "PRAGMA table_info(orders)").fetchall()}
        item_columns = {row[1] for row in connection.execute(
            "PRAGMA table_info(order_items)").fetchall()}
        order_fks = connection.execute("PRAGMA foreign_key_list(orders)").fetchall()
        item_fks = connection.execute("PRAGMA foreign_key_list(order_items)").fetchall()
        order_indexes = connection.execute("PRAGMA index_list(orders)").fetchall()
        item_indexes = connection.execute("PRAGMA index_list(order_items)").fetchall()
        order_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='orders'").fetchone()[0]
        item_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='order_items'").fetchone()[0]

    assert order_columns == {"id", "buyer_id", "status", "total_amount", "currency",
                             "checkout_nonce", "created_at"}
    assert item_columns == {"id", "order_id", "product_id", "seller_id", "product_title",
                            "seller_username", "unit_price", "currency"}
    assert any(row[2] == "users" and row[3] == "buyer_id" and
               row[6].upper() == "RESTRICT" for row in order_fks)
    assert {(row[2], row[3], row[6].upper()) for row in item_fks} == {
        ("orders", "order_id", "CASCADE"), ("products", "product_id", "RESTRICT"),
        ("users", "seller_id", "RESTRICT")}
    assert any("buyer" in row[1] for row in order_indexes)
    assert any("product" in row[1] for row in item_indexes)
    assert "CHECK" in order_sql.upper() and "CHECK" in item_sql.upper()


def test_order_migration_preserves_mm019_rows_and_downgrades_only_orders(tmp_path):
    application, database_path = make_migration_app(tmp_path, "mm025-existing.sqlite")
    runner = application.test_cli_runner()
    first = runner.invoke(args=["db", "upgrade", "f19c7a42e0b1"])
    assert first.exit_code == 0, first.output
    with sqlite3.connect(database_path) as connection:
        connection.execute("INSERT INTO users "
            "(id,username,email,password_hash,enabled,personalization,created_at,updated_at) "
            "VALUES (1,'order-seller','seller@order.test','hash',1,0,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),"
            "(2,'order-buyer','buyer@order.test','hash',1,0,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)")
        connection.execute("INSERT INTO products "
            "(id,version,seller_id,title,description,price,currency,category,condition,status,created_at,updated_at) "
            "VALUES (1,1,1,'Existing order item','Description long enough',1299,'USD','other','good','active',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)")
        connection.execute("INSERT INTO cart_items (user_id,product_id,added_at) "
                           "VALUES (2,1,CURRENT_TIMESTAMP)")
        connection.commit()

    upgrade = runner.invoke(args=["db", "upgrade"])
    assert upgrade.exit_code == 0, upgrade.output
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT username FROM users WHERE id=2").fetchone() == ("order-buyer",)
        assert connection.execute("SELECT title,price FROM products").fetchone() == ("Existing order item", 1299)
        assert connection.execute("SELECT user_id,product_id FROM cart_items").fetchone() == (2, 1)

    downgrade = runner.invoke(args=["db", "downgrade", "f19c7a42e0b1"])
    assert downgrade.exit_code == 0, downgrade.output
    remaining = table_names(database_path)
    assert "orders" not in remaining and "order_items" not in remaining
    assert {"users", "products", "cart_items"} <= remaining
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("SELECT user_id,product_id FROM cart_items").fetchone() == (2, 1)


def test_order_migration_raw_uniqueness_and_checks(tmp_path):
    application, database_path = make_migration_app(tmp_path, "mm025-raw.sqlite")
    runner = application.test_cli_runner()
    result = runner.invoke(args=["db", "upgrade"])
    assert result.exit_code == 0, result.output
    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("INSERT INTO users "
            "(id,username,email,password_hash,enabled,personalization,created_at,updated_at) "
            "VALUES (1,'raw-seller','seller@raw.test','hash',1,0,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP),"
            "(2,'raw-buyer','buyer@raw.test','hash',1,0,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)")
        connection.execute("INSERT INTO products "
            "(id,version,seller_id,title,description,price,currency,category,condition,status,created_at,updated_at) "
            "VALUES (1,1,1,'Raw order product','Description long enough',2500,'USD','other','good','sold',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)")
        connection.execute("INSERT INTO orders "
            "(id,buyer_id,status,total_amount,currency,checkout_nonce,created_at) "
            "VALUES (1,2,'completed',2500,'USD','raw-valid-checkout-nonce',CURRENT_TIMESTAMP)")
        connection.execute("INSERT INTO order_items "
            "(order_id,product_id,seller_id,product_title,seller_username,unit_price,currency) "
            "VALUES (1,1,1,'Raw order product','raw-seller',2500,'USD')")
        connection.commit()

        try:
            connection.execute("INSERT INTO orders "
                "(buyer_id,status,total_amount,currency,checkout_nonce,created_at) "
                "VALUES (2,'completed',2500,'USD','raw-valid-checkout-nonce',CURRENT_TIMESTAMP)")
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("Duplicate buyer/nonce was accepted")

        try:
            connection.execute("INSERT INTO orders "
                "(buyer_id,status,total_amount,currency,checkout_nonce,created_at) "
                "VALUES (2,'pending',2500,'USD','another-valid-checkout-nonce',CURRENT_TIMESTAMP)")
        except sqlite3.IntegrityError:
            pass
        else:
            raise AssertionError("Unsupported order status was accepted")

