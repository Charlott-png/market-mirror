"""MM-015 operational contracts and maintenance safety."""

from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest


def test_production_requires_secret_database_and_hosts(monkeypatch):
    from app import create_app
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValueError):
        create_app()
    monkeypatch.setenv("SECRET_KEY", "x" * 40)
    with pytest.raises(ValueError):
        create_app()
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    with pytest.raises(ValueError):
        create_app()


def test_readiness_database_failure_and_health_contract(db_app, monkeypatch):
    from app.extensions import db
    from sqlalchemy.exc import OperationalError
    client = db_app.test_client()
    assert client.get("/ready").status_code == 200
    def unavailable(*args, **kwargs):
        raise OperationalError("private-path", {}, Exception("private-secret"))
    monkeypatch.setattr(db.session, "execute", unavailable)
    response = client.get("/ready")
    assert response.status_code == 503 and response.json == {"status": "unavailable"}
    assert b"private" not in response.data
    assert client.get("/health").json == {"service": "market-mirror", "status": "ok"}


def test_retention_and_anonymization_preserve_marketplace_history(db_app, user_factory, product_factory):
    from app.extensions import db
    from app.models import InteractionEvent, SavedProduct, User, Product
    user = user_factory()
    other = user_factory()
    owned = product_factory(seller=user)
    listing = product_factory(seller=other)
    db.session.add(InteractionEvent(user_id=user.id, product_id=listing.id, kind="view", window=1,
        created_at=datetime.now(timezone.utc) - timedelta(days=91)))
    db.session.add(SavedProduct(user_id=user.id, product_id=listing.id))
    db.session.commit()
    runner = db_app.test_cli_runner()
    assert runner.invoke(args=["maintenance", "purge"]).exit_code == 0
    assert db.session.query(InteractionEvent).count() == 0
    user_id, product_id = user.id, owned.id
    refusal = runner.invoke(args=["maintenance", "anonymize", str(user_id)])
    assert refusal.exit_code != 0
    result = runner.invoke(args=["maintenance", "anonymize", str(user_id), "--confirm-verified-request"])
    assert result.exit_code == 0, result.output
    db.session.expire_all()
    stored = db.session.get(User, user_id)
    assert stored.enabled is False and stored.bio is None and not stored.personalization
    assert stored.email.startswith("deleted-")
    assert db.session.get(Product, product_id).status == "archived"
    assert db.session.query(SavedProduct).filter_by(user_id=user_id).count() == 0


def test_image_reconciliation_is_readonly_by_default(db_app, tmp_path):
    root = tmp_path / "uploads"
    root.mkdir()
    orphan = root / ("a" * 32 + ".jpg")
    orphan.write_bytes(b"orphan-test-file")
    unrelated = root / "do-not-remove.txt"
    unrelated.write_text("keep", encoding="utf-8")
    db_app.config["UPLOAD_FOLDER"] = str(root)
    runner = db_app.test_cli_runner()
    result = runner.invoke(args=["maintenance", "images"])
    assert result.exit_code == 0 and orphan.exists()
    result = runner.invoke(args=["maintenance", "images", "--delete-orphans"])
    assert result.exit_code == 0 and not orphan.exists() and unrelated.exists()
