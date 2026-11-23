"""Regression tests for the local active-listing image recovery tool."""

import json
from pathlib import Path
import sqlite3

from PIL import Image
import pytest


MISSING_NAME = "a" * 32 + ".jpg"


def recovery_project(tmp_path, *, include_unmapped=False):
    root = tmp_path / "market-mirror"
    uploads = root / "instance" / "uploads"
    assets = root / "assets" / "recovered-products" / "fixture"
    uploads.mkdir(parents=True)
    assets.mkdir(parents=True)
    database = root / "instance" / "market-mirror.sqlite"
    with sqlite3.connect(database) as connection:
        connection.executescript("""
            PRAGMA foreign_keys=ON;
            CREATE TABLE users (
                id INTEGER PRIMARY KEY, username TEXT NOT NULL
            );
            CREATE TABLE products (
                id INTEGER PRIMARY KEY, seller_id INTEGER NOT NULL,
                title TEXT NOT NULL, status TEXT NOT NULL,
                image_filename TEXT, version INTEGER NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (seller_id) REFERENCES users(id)
            );
            CREATE TABLE product_images (
                id INTEGER PRIMARY KEY, product_id INTEGER NOT NULL,
                filename TEXT NOT NULL UNIQUE, position INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            );
            INSERT INTO users VALUES (1, 'student-seller');
            INSERT INTO products VALUES
                (1, 1, 'Wireless Mouse', 'active', 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.jpg', 3, '2026-01-01'),
                (2, 1, 'Archived Camera', 'archived', 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.jpg', 1, '2026-01-01');
            INSERT INTO product_images VALUES
                (1, 1, 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.jpg', 0, '2026-01-01'),
                (2, 2, 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.jpg', 0, '2026-01-01');
        """)
        if include_unmapped:
            connection.execute("""INSERT INTO products VALUES
                (3, 1, 'Unmapped Active Item', 'active', NULL, 1, '2026-01-01')""")
    source = assets / "wireless-mouse.png"
    Image.new("RGB", (1800, 1200), "navy").save(source)
    manifest = assets / "manifest.json"
    manifest.write_text(json.dumps({"items": [{
        "id": 1, "title": "Wireless Mouse", "owner": "student-seller",
        "file": source.name,
    }]}), encoding="utf-8")
    return root, database, uploads, manifest


def test_recovery_restores_exact_reference_without_changing_listing(tmp_path):
    from scripts.recover_missing_product_images import recover_missing_images

    root, database, uploads, manifest = recovery_project(tmp_path)
    before = sqlite3.connect(database).execute(
        "SELECT image_filename, version, updated_at FROM products WHERE id=1").fetchone()

    report = recover_missing_images(root, manifest)

    destination = uploads / MISSING_NAME
    assert report["repaired_listings"] == 1
    assert report["restored_files"] == 1
    assert destination.is_file()
    with Image.open(destination) as image:
        assert image.format == "JPEG"
        assert max(image.size) <= 1600
        assert image.getexif() == {}
    after = sqlite3.connect(database).execute(
        "SELECT image_filename, version, updated_at FROM products WHERE id=1").fetchone()
    assert after == before

    repeated = recover_missing_images(root, manifest)
    assert repeated["repaired_listings"] == 0
    assert repeated["restored_files"] == 0


def test_recovery_ignores_inactive_listing_even_when_its_file_is_missing(tmp_path):
    from scripts.recover_missing_product_images import scan_missing_images

    root, _, _, manifest = recovery_project(tmp_path)
    report = scan_missing_images(root, manifest)

    assert [item["id"] for item in report["missing"]] == [1]
    assert report["unmapped"] == []


def test_unmapped_active_listing_stops_before_any_file_is_written(tmp_path):
    from scripts.recover_missing_product_images import recover_missing_images

    root, _, uploads, manifest = recovery_project(tmp_path, include_unmapped=True)

    with pytest.raises(RuntimeError, match="generated replacement"):
        recover_missing_images(root, manifest)
    assert list(uploads.iterdir()) == []

