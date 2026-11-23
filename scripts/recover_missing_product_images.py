"""Restore generated photos for active listings whose image files are missing.

The AI-created source PNGs are reviewed project assets. This script does not
call an external API: it detects broken active-listing references, safely
normalizes the matching source to JPEG, and restores the exact referenced file.
Run without arguments to scan; use ``--apply`` to perform the repair.
"""

from contextlib import closing
from datetime import datetime, timezone
from io import BytesIO
import json
import os
from pathlib import Path
import sqlite3
import sys
import uuid

from werkzeug.datastructures import FileStorage


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.images import FILENAME, normalized_image_bytes
from scripts.generate_demo_images import backup_database, safe_child


DEFAULT_MANIFEST = (PROJECT_ROOT / "assets" / "recovered-products" /
                    "2026-11-07" / "manifest.json")


def _paths(project_root):
    root = Path(project_root).resolve()
    instance = safe_child(root, "instance")
    database = safe_child(instance, "market-mirror.sqlite")
    uploads = safe_child(instance, "uploads")
    backups = safe_child(instance, "backups")
    if not database.is_file():
        raise RuntimeError("Existing local Market Mirror database required.")
    return root, database, uploads, backups


def _manifest(project_root, manifest_path):
    root = Path(project_root).resolve()
    path = Path(manifest_path).resolve()
    if not path.is_file() or not path.is_relative_to(root):
        raise ValueError("Recovery manifest must be a project file.")
    document = json.loads(path.read_text(encoding="utf-8"))
    items = document.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("Recovery manifest must contain replacement items.")
    mapped = {}
    for item in items:
        if (not isinstance(item, dict) or type(item.get("id")) is not int
                or not isinstance(item.get("title"), str)
                or not isinstance(item.get("owner"), str)):
            raise ValueError("Recovery manifest contains an invalid listing identity.")
        if item["id"] in mapped:
            raise ValueError("Recovery manifest contains a duplicate product ID.")
        filename = item.get("file")
        if (not isinstance(filename, str) or Path(filename).name != filename
                or Path(filename).suffix.lower() not in {".png", ".jpg", ".jpeg"}):
            raise ValueError("Recovery source must be a simple PNG or JPEG filename.")
        source = (path.parent / filename).resolve()
        if (source.parent != path.parent.resolve() or source.is_symlink()
                or not source.is_file()):
            raise ValueError(f"Generated recovery source is missing: {filename}")
        mapped[item["id"]] = {**item, "source": source}
    return mapped


def _reference_path(uploads, filename):
    if not isinstance(filename, str) or FILENAME.fullmatch(filename) is None:
        raise RuntimeError("Database contains an invalid image reference.")
    destination = uploads / filename
    if destination.is_symlink() or destination.resolve().parent != uploads.resolve():
        raise RuntimeError("Unsafe image destination detected.")
    return destination


def _references(connection, product):
    rows = connection.execute(
        "SELECT filename FROM product_images WHERE product_id=? ORDER BY position, id",
        (product["id"],)).fetchall()
    if rows:
        return [row["filename"] for row in rows]
    return [product["image_filename"]] if product["image_filename"] else []


def scan_missing_images(project_root=PROJECT_ROOT, manifest_path=DEFAULT_MANIFEST):
    """Describe broken active listings without changing files or database rows."""
    root, database, uploads, _ = _paths(project_root)
    replacements = _manifest(root, manifest_path)
    with closing(sqlite3.connect(
            database.as_uri() + "?mode=ro", uri=True)) as connection:
        connection.row_factory = sqlite3.Row
        products = connection.execute("""SELECT p.id, p.title, p.image_filename,
                p.version, u.username
            FROM products p JOIN users u ON u.id=p.seller_id
            WHERE p.status='active' ORDER BY p.id""").fetchall()
        missing = []
        unmapped = []
        for product in products:
            references = _references(connection, product)
            broken = [name for name in references
                      if not _reference_path(uploads, name).is_file()]
            if references and not broken:
                continue
            item = {
                "id": product["id"], "title": product["title"],
                "owner": product["username"], "missing_files": broken,
                "has_reference": bool(references),
            }
            replacement = replacements.get(product["id"])
            if (replacement is None or replacement["title"] != product["title"]
                    or replacement["owner"] != product["username"]):
                unmapped.append(item)
            else:
                item["source"] = replacement["file"]
                missing.append(item)
    return {"missing": missing, "unmapped": unmapped}


def _clean_jpeg(source):
    content = source.read_bytes()
    upload = FileStorage(stream=BytesIO(content), filename=source.name)
    return normalized_image_bytes(upload, max_dimension=1600, quality=88)


def _write_new_file(uploads, filename, content):
    destination = _reference_path(uploads, filename)
    if destination.exists():
        return None
    temporary = uploads / f"{filename}.{uuid.uuid4().hex}.pending"
    try:
        with temporary.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.rename(destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return destination


def recover_missing_images(project_root=PROJECT_ROOT, manifest_path=DEFAULT_MANIFEST):
    """Restore every mapped broken active-listing image as one transaction."""
    if os.environ.get("APP_ENV", "").strip().lower() == "production":
        raise RuntimeError("Local generated-image recovery is disabled in production.")
    root, database, uploads, backups = _paths(project_root)
    replacements = _manifest(root, manifest_path)
    scan = scan_missing_images(root, manifest_path)
    if scan["unmapped"]:
        titles = ", ".join(item["title"] for item in scan["unmapped"])
        raise RuntimeError(
            f"No reviewed generated replacement exists for: {titles}. No files were changed.")
    if not scan["missing"]:
        return {"repaired_listings": 0, "restored_files": 0,
                "backup": None, "items": []}

    backup = backup_database(database, backups)
    uploads.mkdir(parents=True, exist_ok=True)
    created = []
    with closing(sqlite3.connect(database.as_uri() + "?mode=rw", uri=True,
                                 timeout=10, isolation_level=None)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE")
        repaired = []
        try:
            for scanned in scan["missing"]:
                product = connection.execute("""SELECT p.id, p.title, p.status,
                        p.image_filename, p.version, u.username
                    FROM products p JOIN users u ON u.id=p.seller_id WHERE p.id=?""",
                    (scanned["id"],)).fetchone()
                replacement = replacements[scanned["id"]]
                if (product is None or product["status"] != "active"
                        or product["title"] != replacement["title"]
                        or product["username"] != replacement["owner"]):
                    raise RuntimeError("A listing changed during recovery; rolling back.")
                references = _references(connection, product)
                missing_names = [name for name in references
                                 if not _reference_path(uploads, name).is_file()]
                clean = _clean_jpeg(replacement["source"])
                attached_new_reference = False
                if not references:
                    missing_names = [uuid.uuid4().hex + ".jpg"]
                    attached_new_reference = True
                restored = []
                for filename in missing_names:
                    destination = _write_new_file(uploads, filename, clean)
                    if destination is not None:
                        created.append(destination)
                        restored.append(filename)
                if attached_new_reference:
                    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
                    updated = connection.execute("""UPDATE products
                        SET image_filename=?, version=version+1, updated_at=?
                        WHERE id=? AND version=? AND image_filename IS NULL""",
                        (missing_names[0], now, product["id"], product["version"]))
                    if updated.rowcount != 1:
                        raise RuntimeError("A listing changed during recovery; rolling back.")
                    connection.execute("""INSERT INTO product_images
                        (product_id, filename, position, created_at) VALUES (?, ?, 0, ?)""",
                        (product["id"], missing_names[0], now))
                if restored:
                    repaired.append({"id": product["id"], "title": product["title"],
                                     "files": restored})
            connection.commit()
        except BaseException:
            connection.rollback()
            for path in created:
                path.unlink(missing_ok=True)
            raise
    return {"repaired_listings": len(repaired),
            "restored_files": sum(len(item["files"]) for item in repaired),
            "backup": backup, "items": repaired}


def main(arguments=None):
    arguments = sys.argv[1:] if arguments is None else arguments
    if arguments not in ([], ["--apply"]):
        print("Usage: python scripts/recover_missing_product_images.py [--apply]",
              file=sys.stderr)
        return 2
    try:
        report = (recover_missing_images() if arguments == ["--apply"]
                  else scan_missing_images())
    except (OSError, sqlite3.Error, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"Image recovery stopped: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, default=str))
    if not arguments:
        print("Scan only. Add --apply to restore the reviewed generated photos.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
