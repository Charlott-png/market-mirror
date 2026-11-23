"""Add the requested ten fictional listings and their generated product pictures.

This is local demo-data preparation, not a new application feature. It reuses
existing model validation, image storage and backup helpers. No existing row or
photo is changed. Repeating an unchanged successful batch does nothing.
"""

from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
import sqlite3
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask
from werkzeug.datastructures import FileStorage

from app.commands import DEMO_USERS
from app.images import discard_image, image_exists, store_image
from app.models import Product
from scripts.generate_demo_images import backup_database, safe_child

BATCH_ID = "extra-demo-2026-10-26"


def add_listings(project_root, manifest_path):
    if os.environ.get("APP_ENV", "").strip().lower() == "production":
        raise RuntimeError("Additional demo listings are disabled in production.")
    root = Path(project_root).resolve()
    instance = safe_child(root, "instance")
    database = safe_child(instance, "market-mirror.sqlite")
    uploads = safe_child(instance, "uploads")
    backups = safe_child(instance, "backups")
    if not database.is_file():
        raise RuntimeError("Existing local database required; nothing was created.")
    manifest_path = Path(manifest_path).resolve()
    if not manifest_path.is_relative_to(root):
        raise ValueError("The manifest must be inside this project.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = manifest["items"]
    if manifest.get("batch_id") != BATCH_ID or len(items) != 10:
        raise ValueError("Expected the reviewed ten-item demo batch.")
    validated = []
    for item in items:
        owner = item["owner"]
        if type(owner) is not int or not 0 <= owner < len(DEMO_USERS):
            raise ValueError("Invalid demo owner.")
        filename = item["file"]
        if Path(filename).name != filename or Path(filename).suffix.lower() != ".png":
            raise ValueError("Expected a simple PNG asset filename.")
        source = safe_child(manifest_path.parent, filename)
        if not source.is_file():
            raise ValueError("A generated image is missing.")
        description = (f"Fictional demonstration listing: {item['title']}. {item['description']} "
            "AI-generated picture and invented demo price, not a market valuation. "
            f"For project practice only. [{BATCH_ID}]")
        # The same validators used by the main app check text, exact Decimal
        # money and allowed choices before any files or database rows are added.
        product = Product(title=item["title"], description=description,
            price=Decimal(item["price"]), currency="USD", category=item["category"],
            condition=item["condition"], status="active")
        validated.append((product, owner, source))
    if len({product.title for product, _, _ in validated}) != 10:
        raise ValueError("The batch must have ten distinct titles.")

    application = Flask("market-mirror-extra-demo-data")
    application.config["UPLOAD_FOLDER"] = str(uploads)
    with application.app_context(), closing(sqlite3.connect(
            database.as_uri() + "?mode=rw", uri=True, isolation_level=None, timeout=5)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE")
        created = []
        receipt = None
        try:
            seller_ids = []
            for username, email in DEMO_USERS:
                found = connection.execute("SELECT id FROM users WHERE username=? AND email=?",
                                           (username, email)).fetchall()
                if len(found) != 1:
                    raise RuntimeError("A demo seller identity is missing or changed; no users were created.")
                seller_ids.append(found[0]["id"])
            marker = f"[{BATCH_ID}]"
            prior = connection.execute("SELECT * FROM products WHERE instr(description,?) > 0", (marker,)).fetchall()
            if prior:
                expected = {(p.title, seller_ids[owner], p.description) for p, owner, _ in validated}
                actual = {(row["title"], row["seller_id"], row["description"]) for row in prior}
                if len(prior) != 10 or actual != expected or not all(image_exists(row["image_filename"]) for row in prior):
                    raise RuntimeError("Existing demo batch is incomplete or has a conflict; nothing was changed.")
                connection.rollback()
                return {"added": 0, "skipped": 10, "backup": None}
            for product, owner, _ in validated:
                if connection.execute("SELECT 1 FROM products WHERE title=? AND seller_id=?",
                                      (product.title, seller_ids[owner])).fetchone():
                    raise RuntimeError("Existing listing title conflict; no records were overwritten.")

            backup = backup_database(database, backups)
            added = []
            for product, owner, source in validated:
                with source.open("rb") as stream:
                    filename = store_image(FileStorage(stream=stream, filename=source.name))
                created.append(filename)
                now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
                # SQLite stores exact integer cents; no floating-point prices.
                result = connection.execute("""INSERT INTO products
                    (seller_id,title,description,price,currency,category,condition,status,
                     image_filename,version,created_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,'active',?,1,?,?)""",
                    (seller_ids[owner], product.title, product.description, int(product.price * 100),
                     product.currency, product.category, product.condition, filename, now, now))
                added.append({"id": result.lastrowid, "title": product.title, "image_filename": filename})
            receipt = backup.with_suffix(".json")
            receipt.write_text(json.dumps({"batch_id": BATCH_ID, "items": added}, indent=2), encoding="utf-8")
            connection.commit()
        except BaseException:
            connection.rollback()
            for filename in created:
                discard_image(filename)
            if receipt is not None:
                receipt.unlink(missing_ok=True)
            raise
        return {"added": 10, "skipped": 0, "backup": backup, "items": added}


if __name__ == "__main__":
    if sys.argv[1:] != ["--apply"]:
        raise SystemExit("Run with --apply to insert the reviewed ten-item local demo batch.")
    result = add_listings(PROJECT_ROOT,
        PROJECT_ROOT / "assets/generated-products/additional-items-2026-10-26/manifest.json")
    print(json.dumps(result, indent=2, default=str))
