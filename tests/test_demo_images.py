"""Test the standalone demo-image helper without touching the student's database."""

import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

import pytest
from PIL import Image

from app.commands import DEMO_PRODUCTS


@pytest.fixture
def demo_project(tmp_path, monkeypatch):
    from app import create_app
    from app.extensions import db

    monkeypatch.delenv("APP_ENV", raising=False)
    root = tmp_path / "project with spaces"
    (root / "instance").mkdir(parents=True)
    database = root / "instance" / "market-mirror.sqlite"
    application = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database.as_posix()}",
        "UPLOAD_FOLDER": str(root / "instance" / "uploads"),
    })
    with application.app_context():
        db.create_all()
    result = application.test_cli_runner().invoke(args=["seed"])
    assert result.exit_code == 0
    yield root, application
    with application.app_context():
        db.session.remove()
        db.engine.dispose()


def rows(root, sql="SELECT * FROM products ORDER BY id", args=()):
    with sqlite3.connect(root / "instance" / "market-mirror.sqlite") as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(sql, args)]


@pytest.mark.parametrize("title", [item[1] for item in DEMO_PRODUCTS])
def test_each_seed_product_has_a_deterministic_readable_illustration(title):
    from scripts.generate_demo_images import draw_product

    image = draw_product(title)
    assert image.mode == "RGB"
    assert image.size == (1200, 900)
    assert image.tobytes() == draw_product(title).tobytes()
    assert len(image.getcolors(image.width * image.height)) > 50


def test_all_artworks_are_distinct():
    from scripts.generate_demo_images import draw_product

    hashes = {hashlib.sha256(draw_product(item[1]).tobytes()).hexdigest()
              for item in DEMO_PRODUCTS}
    assert len(hashes) == 12


def test_attach_backup_and_public_visibility(demo_project):
    from scripts.generate_demo_images import attach_demo_images

    root, application = demo_project
    before = rows(root)
    users_before = rows(root, "SELECT * FROM users ORDER BY id")
    report = attach_demo_images(root)
    assert report["attached"] == 12
    assert report["skipped"] == 0
    backup = report["backup"]
    assert backup.is_file()
    with sqlite3.connect(backup) as connection:
        connection.row_factory = sqlite3.Row
        assert [dict(row) for row in connection.execute("SELECT * FROM products ORDER BY id")] == before
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    after = rows(root)
    assert rows(root, "SELECT * FROM users ORDER BY id") == users_before
    client = application.test_client()
    for original, updated in zip(before, after):
        for key in original.keys() - {"image_filename", "version", "updated_at"}:
            assert updated[key] == original[key]
        assert updated["version"] == original["version"] + 1
        filename = updated["image_filename"]
        assert len(filename) == 36 and filename.endswith(".jpg")
        with Image.open(root / "instance" / "uploads" / filename) as picture:
            assert picture.format == "JPEG" and picture.size == (1200, 900)
            assert not picture.getexif()
        response = client.get(f"/media/products/{filename}")
        assert response.status_code == (404 if updated["status"] == "archived" else 200)
    assert not list((root / "instance" / "uploads").glob("*.pending"))


def test_rerun_is_a_no_op(demo_project):
    from scripts.generate_demo_images import attach_demo_images

    root, _ = demo_project
    attach_demo_images(root)
    before = rows(root)
    files = {path.name: path.read_bytes() for path in (root / "instance" / "uploads").iterdir()}
    report = attach_demo_images(root)
    assert report == {"attached": 0, "skipped": 12, "backup": None}
    assert rows(root) == before
    assert {path.name: path.read_bytes() for path in (root / "instance" / "uploads").iterdir()} == files
    assert len(list((root / "instance" / "backups").iterdir())) == 1


def test_existing_photos_and_modified_listings_are_preserved(demo_project):
    from scripts.generate_demo_images import attach_demo_images

    root, _ = demo_project
    uploads = root / "instance" / "uploads"
    uploads.mkdir()
    existing = uploads / ("a" * 32 + ".jpg")
    existing.write_bytes(b"existing owner's file")
    with sqlite3.connect(root / "instance" / "market-mirror.sqlite") as connection:
        connection.execute("UPDATE products SET image_filename=? WHERE id=1", (existing.name,))
        # A broken existing reference must not be silently replaced either.
        connection.execute("UPDATE products SET image_filename=? WHERE id=2", ("b" * 32 + ".jpg",))
        connection.execute("UPDATE products SET description='A changed description by the student.' WHERE id=3")
        connection.execute("UPDATE products SET seller_id=2 WHERE id=4")
    before = rows(root)
    report = attach_demo_images(root)
    assert report["attached"] == 8 and report["skipped"] == 2
    assert rows(root)[:4] == before[:4]
    assert existing.read_bytes() == b"existing owner's file"


def test_failure_rolls_back_rows_and_only_removes_new_files(demo_project, monkeypatch):
    from scripts import generate_demo_images as helper

    root, _ = demo_project
    uploads = root / "instance" / "uploads"
    uploads.mkdir()
    old = uploads / "keep-me.txt"
    old.write_text("untouched", encoding="utf-8")
    before = rows(root)
    original = helper.draw_product
    count = 0

    def fail_second(title):
        nonlocal count
        count += 1
        if count == 2:
            raise OSError("simulated disk/rendering failure")
        return original(title)

    monkeypatch.setattr(helper, "draw_product", fail_second)
    with pytest.raises(OSError):
        helper.attach_demo_images(root)
    assert rows(root) == before
    assert list(uploads.iterdir()) == [old]
    assert len(list((root / "instance" / "backups").iterdir())) == 1


def test_database_update_failure_cleans_images(demo_project):
    from scripts.generate_demo_images import attach_demo_images

    root, _ = demo_project
    before = rows(root)
    with sqlite3.connect(root / "instance" / "market-mirror.sqlite") as connection:
        connection.execute("""CREATE TRIGGER refuse_demo_update BEFORE UPDATE ON products
                              WHEN NEW.id=2 BEGIN SELECT RAISE(ABORT, 'test failure'); END""")
    with pytest.raises(sqlite3.DatabaseError):
        attach_demo_images(root)
    assert rows(root) == before
    assert not list((root / "instance" / "uploads").iterdir())


def test_production_is_refused_without_changes(demo_project, monkeypatch):
    from scripts.generate_demo_images import attach_demo_images

    root, _ = demo_project
    before = rows(root)
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError, match="production"):
        attach_demo_images(root)
    assert rows(root) == before
    assert not (root / "instance" / "uploads").exists()


def test_missing_database_is_not_created(tmp_path, monkeypatch):
    from scripts.generate_demo_images import attach_demo_images

    monkeypatch.delenv("APP_ENV", raising=False)
    with pytest.raises(RuntimeError, match="database"):
        attach_demo_images(tmp_path)
    assert not (tmp_path / "instance").exists()


def test_unknown_title_is_not_generic_art():
    from scripts.generate_demo_images import draw_product

    with pytest.raises(ValueError, match="Unknown"):
        draw_product("A real student's phone")


def test_no_seed_matches_does_not_create_art(demo_project):
    from scripts.generate_demo_images import attach_demo_images

    root, _ = demo_project
    with sqlite3.connect(root / "instance" / "market-mirror.sqlite") as connection:
        connection.execute("UPDATE users SET email=username || '@real.example'")
    with pytest.raises(RuntimeError, match="demo listings"):
        attach_demo_images(root)
    assert not (root / "instance" / "uploads").exists()


def test_duplicate_seed_match_is_refused(demo_project):
    from scripts.generate_demo_images import attach_demo_images

    root, _ = demo_project
    with sqlite3.connect(root / "instance" / "market-mirror.sqlite") as connection:
        connection.execute("""INSERT INTO products
            (seller_id,title,description,price,currency,category,condition,status,version,created_at,updated_at)
            SELECT seller_id,title,description,price,currency,category,condition,status,version,created_at,updated_at
            FROM products WHERE id=1""")
    before = rows(root)
    with pytest.raises(RuntimeError, match="Duplicate"):
        attach_demo_images(root)
    assert rows(root) == before
    assert not (root / "instance" / "uploads").exists()


def test_script_fixture_names_match_application_seed():
    from app.commands import DEMO_USERS
    from scripts.generate_demo_images import DEMO_SELLERS, DEMO_TITLES

    assert DEMO_SELLERS == DEMO_USERS
    assert DEMO_TITLES == tuple(item[1] for item in DEMO_PRODUCTS)
    assert [item[0] for item in DEMO_PRODUCTS] == [index // 4 for index in range(12)]


def test_backup_failure_prevents_all_updates(demo_project, monkeypatch):
    from scripts import generate_demo_images as helper

    root, _ = demo_project
    before = rows(root)

    def fail_backup(*args):
        raise OSError("simulated full backup disk")

    monkeypatch.setattr(helper, "backup_database", fail_backup)
    with pytest.raises(OSError):
        helper.attach_demo_images(root)
    assert rows(root) == before
    assert not (root / "instance" / "uploads").exists()


def test_commit_failure_rolls_back_all_new_references_and_files(demo_project):
    from scripts.generate_demo_images import attach_demo_images

    root, _ = demo_project
    before = rows(root)
    with sqlite3.connect(root / "instance" / "market-mirror.sqlite") as connection:
        connection.execute("""CREATE TABLE deferred_failure
            (user_id INTEGER REFERENCES users(id) DEFERRABLE INITIALLY DEFERRED)""")
        connection.execute("""CREATE TRIGGER fail_at_commit AFTER UPDATE ON products
            BEGIN INSERT INTO deferred_failure (user_id) VALUES (999999); END""")
    with pytest.raises(sqlite3.IntegrityError):
        attach_demo_images(root)
    assert rows(root) == before
    assert not list((root / "instance" / "uploads").iterdir())


def test_redirected_folder_is_rejected_before_any_changes(demo_project, monkeypatch):
    from scripts.generate_demo_images import attach_demo_images

    root, _ = demo_project
    before = rows(root)
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda self: self.name == "uploads" or original(self))
    with pytest.raises(RuntimeError, match="Unsafe"):
        attach_demo_images(root)
    assert rows(root) == before
    assert not (root / "instance" / "backups").exists()


def test_command_from_another_folder_ignores_external_database_environment(demo_project, tmp_path):
    root, _ = demo_project
    script = root / "scripts" / "generate_demo_images.py"
    script.parent.mkdir()
    source = Path(__file__).resolve().parents[1] / "scripts" / "generate_demo_images.py"
    shutil.copy2(source, script)
    environment = os.environ.copy()
    outside = tmp_path / "must-not-create.sqlite"
    environment.update(DATABASE_URL=f"sqlite:///{outside.as_posix()}",
                       UPLOAD_FOLDER=str(tmp_path / "must-not-create-uploads"))
    result = subprocess.run([sys.executable, str(script)], cwd=tmp_path,
                            env=environment, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert "Attached 12 demo illustrations" in result.stdout
    assert not outside.exists()
    assert not (tmp_path / "must-not-create-uploads").exists()
    assert len(list((root / "instance" / "uploads").glob("*.jpg"))) == 12
