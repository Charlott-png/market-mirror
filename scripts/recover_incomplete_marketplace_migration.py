"""One-time recovery of the development-only interrupted d88e8d30439f upgrade.

Refuses unknown revisions or nonempty new tables. Backs up the exact database
before removing only empty objects created by that failed migration.
"""

from pathlib import Path
import sqlite3

root = Path(__file__).resolve().parents[1]
database = root / "instance" / "market-mirror.sqlite"
backup = database.with_name("market-mirror-before-migration-recovery.sqlite")
if not database.is_file() or backup.exists():
    raise SystemExit("Missing database or backup already exists; refusing automatic recovery.")

tables_to_remove = ["read_markers", "messages", "saved_products", "listing_submissions",
                    "interaction_events", "conversations", "rate_limits", "_alembic_tmp_users"]
with sqlite3.connect(database) as connection:
    connection.execute("PRAGMA foreign_keys=ON")
    revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    if revision != ("46b4b94079af",):
        raise SystemExit("Unexpected revision; refusing recovery.")
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for name in tables_to_remove:
        if name in tables and connection.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]:
            raise SystemExit("New tables contain data; manual recovery is required.")
    before_users = connection.execute("SELECT * FROM users ORDER BY id").fetchall()
    before_products = connection.execute("SELECT id,seller_id,title,price FROM products ORDER BY id").fetchall()
    with sqlite3.connect(backup) as snapshot:
        connection.backup(snapshot)
    connection.execute("BEGIN IMMEDIATE")
    for name in tables_to_remove:
        if name in tables:
            connection.execute(f'DROP TABLE "{name}"')
    columns = {row[1] for row in connection.execute("PRAGMA table_info(products)")}
    if "version" in columns:
        connection.execute("ALTER TABLE products DROP COLUMN version")
    assert connection.execute("SELECT * FROM users ORDER BY id").fetchall() == before_users
    assert connection.execute("SELECT id,seller_id,title,price FROM products ORDER BY id").fetchall() == before_products
    connection.commit()
print("Recovered the prior schema; all existing users/products preserved. Backup saved in instance/.")
