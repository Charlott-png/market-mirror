"""Regression checks for attaching generated assets without losing old photos."""

import json
from pathlib import Path
import sqlite3

import pytest
from PIL import Image

from tests.test_demo_images import demo_project, rows


def prepare_manifest(root):
    folder = root / "assets"
    folder.mkdir()
    items = []
    for row in rows(root)[:2]:
        name = f"product-{row['id']}.png"
        Image.new("RGB", (100, 100), "blue").save(folder / name)
        items.append({"id": row["id"], "title": row["title"], "old": None, "file": name})
    manifest = folder / "manifest.json"
    manifest.write_text(json.dumps({"items": items}), encoding="utf-8")
    return manifest


def test_asset_import_preserves_every_other_field(demo_project):
    from scripts.attach_generated_product_assets import attach_assets

    root, _ = demo_project
    manifest = prepare_manifest(root)
    before = rows(root)
    result = attach_assets(root, manifest)
    assert result["attached"] == 2
    assert result["backup"].is_file()
    after = rows(root)
    for original, updated in zip(before, after):
        if original["id"] > 2:
            assert original == updated
        else:
            assert updated["version"] == original["version"] + 1
            assert updated["image_filename"] != original["image_filename"]
            for field in original.keys() - {"image_filename", "version", "updated_at"}:
                assert updated[field] == original[field]
            with Image.open(root / "instance" / "uploads" / updated["image_filename"]) as image:
                assert image.format == "JPEG"


def test_stale_manifest_cannot_replace_a_new_photo(demo_project):
    from scripts.attach_generated_product_assets import attach_assets

    root, _ = demo_project
    manifest = prepare_manifest(root)
    attach_assets(root, manifest)
    before = rows(root)
    with pytest.raises(RuntimeError, match="changed"):
        attach_assets(root, manifest)
    assert rows(root) == before


def test_bad_image_rolls_back_whole_batch(demo_project):
    from scripts.attach_generated_product_assets import attach_assets

    root, _ = demo_project
    manifest = prepare_manifest(root)
    (manifest.parent / "product-2.png").write_bytes(b"not an image")
    before = rows(root)
    with pytest.raises(ValueError):
        attach_assets(root, manifest)
    assert rows(root) == before
    assert not list((root / "instance" / "uploads").glob("*.jpg"))


def test_prior_photo_is_retained_and_backed_up(demo_project):
    from scripts.attach_generated_product_assets import attach_assets

    root, _ = demo_project
    manifest = prepare_manifest(root)
    data = json.loads(manifest.read_text())
    old = "a" * 32 + ".jpg"
    uploads = root / "instance" / "uploads"
    uploads.mkdir()
    Image.new("RGB", (90, 90), "red").save(uploads / old)
    old_bytes = (uploads / old).read_bytes()
    with sqlite3.connect(root / "instance" / "market-mirror.sqlite") as connection:
        connection.execute("UPDATE products SET image_filename=? WHERE id=1", (old,))
    data["items"][0]["old"] = old
    manifest.write_text(json.dumps(data))
    result = attach_assets(root, manifest)
    assert (uploads / old).read_bytes() == old_bytes
    assert (result["backup"].parent / "original-uploads" / old).read_bytes() == old_bytes


def test_production_is_refused(demo_project, monkeypatch):
    from scripts.attach_generated_product_assets import attach_assets

    root, _ = demo_project
    manifest = prepare_manifest(root)
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError, match="production"):
        attach_assets(root, manifest)
