"""Readiness and explicit, auditable local operator maintenance."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import secrets
import time

import click
from flask import Blueprint, current_app, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.images import image_exists, image_path
from app.models import (User, Product, ProductImage, InteractionEvent, RateLimit,
                        SavedProduct, Message)

operations = Blueprint("operations", __name__)


@operations.get("/ready")
def ready():
    try:
        db.session.execute(text("SELECT 1 FROM users LIMIT 1"))
        return jsonify(status="ready")
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify(status="unavailable"), 503


def register_maintenance(application):
    @application.cli.group("maintenance")
    def maintenance():
        """Operator-only data and media maintenance (no public admin endpoint)."""

    @maintenance.command("purge")
    def purge():
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        events = db.session.execute(db.delete(InteractionEvent).where(InteractionEvent.created_at < cutoff)).rowcount
        counters = db.session.execute(db.delete(RateLimit).where(RateLimit.expires_at <= time.time())).rowcount
        db.session.commit()
        click.echo(f"Removed {events} expired events and {counters} expired throttle counters.")

    @maintenance.command("anonymize")
    @click.argument("user_id", type=int)
    @click.option("--confirm-verified-request", is_flag=True, help="Confirm the operator verified identity and deletion scope.")
    def anonymize(user_id, confirm_verified_request):
        if not confirm_verified_request:
            raise click.ClickException("Verify the user's request first; then pass --confirm-verified-request.")
        user = db.session.get(User, user_id)
        if user is None:
            raise click.ClickException("Account not found.")
        # One transaction retains relational history but removes identifying text.
        identifier = "deleted-" + secrets.token_hex(10)
        user.username = identifier
        user.email = identifier + "@example.invalid"
        user.password_hash = generate_password_hash(secrets.token_urlsafe(48))
        user.enabled, user.personalization, user.bio = False, False, None
        products = db.session.execute(db.select(Product).where(Product.seller_id == user_id).with_for_update()).scalars().all()
        for product in products:
            product.status = "archived"
        db.session.execute(db.delete(SavedProduct).where(SavedProduct.user_id == user_id))
        db.session.execute(db.delete(InteractionEvent).where(InteractionEvent.user_id == user_id))
        db.session.execute(db.update(Message).where(Message.sender_id == user_id).values(body="[Removed at account holder request]"))
        db.session.commit()
        click.echo("Account disabled and anonymized; listings archived; relational history retained. Review listing text/media and backups separately.")

    @maintenance.command("images")
    @click.option("--delete-orphans", is_flag=True)
    def images(delete_orphans):
        root = Path(current_app.config["UPLOAD_FOLDER"])
        if root.is_symlink():
            raise click.ClickException("Refusing a symlinked upload root.")
        references = set(db.session.execute(db.select(Product.image_filename).where(
            Product.image_filename.is_not(None))).scalars())
        references.update(db.session.execute(db.select(ProductImage.filename)).scalars())
        covers = db.session.execute(db.select(Product.image_filename, ProductImage.filename).join(
            ProductImage, (ProductImage.product_id == Product.id) &
                          (ProductImage.position == 0))).all()
        cover_drift = sum(cover != first for cover, first in covers)
        missing = sum(not image_exists(name) for name in references)
        orphan_count = 0
        if root.exists():
            for path in root.iterdir():
                if path.is_symlink() or not path.is_file() or path.name in references:
                    continue
                try:
                    safe = image_path(path.name)
                except ValueError:
                    continue
                orphan_count += 1
                if delete_orphans:
                    safe.unlink()
        click.echo(f"{missing} missing referenced images; {cover_drift} cover drift; "
                   f"{orphan_count} orphan JPEGs "
                   f"{'deleted' if delete_orphans else 'reported (read-only)'}. Stop writers before deleting orphans.")
