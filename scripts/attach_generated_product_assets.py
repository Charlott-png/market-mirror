"""Attach the reviewed 2026-10-26 AI assets to existing fictional seed listings.

No AI/API calls happen here. Source PNGs were generated with the built-in image
tool and are saved in assets/generated-products/2026-10-26 alongside their prompts.
Use --apply explicitly. This one-time importer refuses changed photo references;
it never replaces a newer user upload or deletes an original picture.
"""

from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import uuid

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask
from werkzeug.datastructures import FileStorage

from app.commands import DEMO_PRODUCTS, DEMO_USERS
from app.images import discard_image, image_path, store_image
from scripts.generate_demo_images import backup_database, safe_child


def attach_assets(project_root, manifest_path):
    if os.environ.get("APP_ENV", "").strip().lower() == "production":
        raise RuntimeError("Generated demo assets are disabled in production.")
    root = Path(project_root).resolve()
    instance = safe_child(root, "instance")
    database = safe_child(instance, "market-mirror.sqlite")
    uploads = safe_child(instance, "uploads")
    backups = safe_child(instance, "backups")
    if not database.is_file():
        raise RuntimeError("Existing local database required.")
    manifest_path = Path(manifest_path).resolve()
    if not manifest_path.is_relative_to(root):
        raise ValueError("Asset manifest must be inside the project.")
    items = json.loads(manifest_path.read_text(encoding="utf-8"))["items"]
    if not items or len({item["id"] for item in items}) != len(items):
        raise ValueError("Asset list must be nonempty with unique product IDs.")
    seed_owners = {product[1]: DEMO_USERS[product[0]] for product in DEMO_PRODUCTS}
    application = Flask("market-mirror-generated-assets")
    application.config["UPLOAD_FOLDER"] = str(uploads)

    with application.app_context(), closing(sqlite3.connect(
            database.as_uri() + "?mode=rw", uri=True, timeout=5, isolation_level=None)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE")
        created = []
        try:
            selected = []
            for item in items:
                row = connection.execute("""SELECT p.*, u.username, u.email
                    FROM products p JOIN users u ON u.id=p.seller_id WHERE p.id=?""",
                    (item["id"],)).fetchone()
                if (row is None or row["title"] != item["title"]
                        or (row["username"], row["email"]) != seed_owners.get(item["title"])
                        or row["description"] != f"Fictional demonstration listing: {item['title']}. For project practice only."):
                    raise RuntimeError("Listing identity changed; refusing to attach assets.")
                if row["image_filename"] != item["old"]:
                    raise RuntimeError("A photo reference changed; refusing to replace a newer photo.")
                filename = item["file"]
                if Path(filename).name != filename or Path(filename).suffix.lower() != ".png":
                    raise ValueError("Expected a simple PNG asset filename.")
                source = safe_child(manifest_path.parent, filename)
                if not source.is_file():
                    raise ValueError("Generated source asset is missing.")
                if item["old"]:
                    image_path(item["old"])  # Validate the old reference before any copies.
                selected.append((item, row, source))

            # Keep the old database AND copies of original uploads together.
            # Originals also remain in uploads; future orphan cleanup cannot
            # destroy the independent copies in this recovery folder.
            recovery = backups / ("ai-" + uuid.uuid4().hex[:12])
            # Keep the snapshot filename short inside the recovery directory:
            # deeply nested Windows project/test paths can hit MAX_PATH.
            snapshot = backup_database(database, backups)
            recovery.mkdir()
            backup = snapshot.rename(recovery / "database.sqlite")
            originals = recovery / "original-uploads"
            originals.mkdir()
            changes = []
            for item, row, source in selected:
                if item["old"] and image_path(item["old"]).is_file():
                    shutil.copy2(image_path(item["old"]), originals / item["old"])
                with source.open("rb") as stream:
                    new_name = store_image(FileStorage(stream=stream, filename=source.name))
                created.append(new_name)
                # Use the app's image validation/JPEG encoding and visibility
                # route; no images are placed in the public static directory.
                now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
                updated = connection.execute("""UPDATE products
                    SET image_filename=?, version=version+1, updated_at=?
                    WHERE id=? AND version=? AND image_filename IS ?""",
                    (new_name, now, row["id"], row["version"], item["old"]))
                if updated.rowcount != 1:
                    raise RuntimeError("Listing changed; rolling back all new attachments.")
                changes.append({"id": row["id"], "title": row["title"],
                                "old": item["old"], "new": new_name})
            (recovery / "replacement-map.json").write_text(
                json.dumps(changes, indent=2), encoding="utf-8")
            connection.commit()
        except BaseException:
            connection.rollback()
            for filename in created:
                discard_image(filename)
            raise
        return {"attached": len(changes), "backup": backup, "changes": changes}


if __name__ == "__main__":
    if sys.argv[1:] != ["--apply"]:
        raise SystemExit("One-time local asset import: run with --apply to update the reviewed listings.")
    report = attach_assets(PROJECT_ROOT,
        PROJECT_ROOT / "assets" / "generated-products" / "2026-10-26" / "manifest.json")
    print(json.dumps(report, indent=2, default=str))
