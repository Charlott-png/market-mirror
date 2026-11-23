"""Test additional fixture insertion before touching the local marketplace."""

import json
from pathlib import Path
import sqlite3

from PIL import Image
import pytest

from tests.test_demo_images import demo_project, rows


def prepare(root):
    source = Path(__file__).resolve().parents[1] / "assets/generated-products/additional-items-2026-10-26/manifest.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    assets = root / "assets"
    assets.mkdir()
    for index, item in enumerate(data["items"]):
        item["file"] = f"item-{index}.png"
        Image.new("RGB", (80, 60), "blue").save(assets / item["file"])
    manifest = assets / "manifest.json"
    manifest.write_text(json.dumps(data), encoding="utf-8")
    return manifest, data


def test_adds_ten_preserves_existing_and_rerun_is_noop(demo_project):
    from scripts.add_additional_demo_items import add_listings

    root, application = demo_project
    manifest, data = prepare(root)
    before = rows(root)
    users = rows(root, "SELECT * FROM users ORDER BY id")
    result = add_listings(root, manifest)
    assert result["added"] == 10 and result["backup"].is_file()
    after = rows(root)
    assert after[:len(before)] == before
    assert len(after) == len(before) + 10
    assert users == rows(root, "SELECT * FROM users ORDER BY id")
    client = application.test_client()
    for item, row in zip(data["items"], after[len(before):]):
        assert row["title"] == item["title"] and row["status"] == "active"
        assert row["price"] == int(float(item["price"]) * 100)
        assert "Fictional demonstration listing" in row["description"]
        assert "not a market valuation" in row["description"]
        assert client.get(f"/products/{row['id']}").status_code == 200
        assert client.get(f"/media/products/{row['image_filename']}").status_code == 200
    again = add_listings(root, manifest)
    assert again["added"] == 0 and again["skipped"] == 10
    assert rows(root) == after
    assert len(list((root / "instance/uploads").glob("*.jpg"))) == 10
    assert len(list((root / "instance/backups").glob("*.sqlite"))) == 1


def test_corrupt_image_rolls_back_all_new_rows_and_files(demo_project):
    from scripts.add_additional_demo_items import add_listings

    root, _ = demo_project
    manifest, _ = prepare(root)
    (manifest.parent / "item-5.png").write_bytes(b"bad image")
    before = rows(root)
    with pytest.raises(ValueError):
        add_listings(root, manifest)
    assert rows(root) == before
    assert not list((root / "instance/uploads").glob("*.jpg"))


def test_wrong_demo_identity_is_refused(demo_project):
    from scripts.add_additional_demo_items import add_listings

    root, _ = demo_project
    manifest, _ = prepare(root)
    with sqlite3.connect(root / "instance/market-mirror.sqlite") as connection:
        connection.execute("UPDATE users SET email='another@example.test' WHERE username='demo-alex'")
    before = rows(root)
    with pytest.raises(RuntimeError, match="identity"):
        add_listings(root, manifest)
    assert rows(root) == before
    assert not (root / "instance/backups").exists()


def test_same_title_collision_is_not_overwritten(demo_project):
    from scripts.add_additional_demo_items import add_listings

    root, _ = demo_project
    manifest, data = prepare(root)
    with sqlite3.connect(root / "instance/market-mirror.sqlite") as connection:
        connection.execute("""INSERT INTO products
            (seller_id,title,description,price,currency,category,condition,status,version,created_at,updated_at)
            SELECT seller_id,?,description,price,currency,category,condition,status,version,created_at,updated_at
            FROM products WHERE id=1""", (data["items"][0]["title"],))
    before = rows(root)
    with pytest.raises(RuntimeError, match="conflict"):
        add_listings(root, manifest)
    assert rows(root) == before


def test_database_failure_rolls_back_rows_and_files(demo_project):
    from scripts.add_additional_demo_items import add_listings

    root, _ = demo_project
    manifest, data = prepare(root)
    with sqlite3.connect(root / "instance/market-mirror.sqlite") as connection:
        connection.execute("""CREATE TRIGGER deny_new_demo BEFORE INSERT ON products
            WHEN NEW.title='Digital camera' BEGIN SELECT RAISE(ABORT, 'test'); END""")
    before = rows(root)
    with pytest.raises(sqlite3.DatabaseError):
        add_listings(root, manifest)
    assert rows(root) == before
    assert not list((root / "instance/uploads").glob("*.jpg"))


def test_production_and_invalid_inputs_are_refused(demo_project, monkeypatch):
    from scripts.add_additional_demo_items import add_listings

    root, _ = demo_project
    manifest, data = prepare(root)
    before = rows(root)
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError, match="production"):
        add_listings(root, manifest)
    monkeypatch.setenv("APP_ENV", "development")
    for field, invalid in [("price", "1.234"), ("price", "NaN"),
                           ("category", "unknown"), ("file", "../outside.png"), ("owner", -1)]:
        altered = json.loads(json.dumps(data))
        altered["items"][0][field] = invalid
        manifest.write_text(json.dumps(altered))
        with pytest.raises((ValueError, RuntimeError)):
            add_listings(root, manifest)
    assert rows(root) == before
    assert not (root / "instance/backups").exists()
