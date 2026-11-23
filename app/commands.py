"""Explicit, transactional creation of fictional development data."""

from decimal import Decimal
import secrets

import click
from flask import current_app
from flask.cli import with_appcontext
from sqlalchemy import or_, select
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import Product, User

DEMO_USERS = (
    ("demo-alex", "alex@example.test"),
    ("demo-blair", "blair@example.test"),
    ("demo-casey", "casey@example.test"),
)
DEMO_PRODUCTS = (
    (0, "Study desk lamp", "home_garden", "good", "active", "18.50"),
    (0, "Python learning book", "books_media", "like_new", "active", "24.00"),
    (0, "Wireless keyboard", "electronics", "good", "sold", "35.99"),
    (0, "Canvas tote bag", "clothing", "new", "archived", "9.25"),
    (1, "Basketball", "sports_outdoors", "good", "active", "16.00"),
    (1, "Board game collection", "toys_games", "like_new", "active", "42.75"),
    (1, "Portable speaker", "electronics", "fair", "active", "21.50"),
    (1, "Ceramic plant pot", "home_garden", "new", "sold", "11.00"),
    (2, "Winter jacket", "clothing", "good", "active", "55.00"),
    (2, "Adventure novel set", "books_media", "fair", "active", "14.99"),
    (2, "Camping lantern", "sports_outdoors", "like_new", "active", "28.00"),
    (2, "Craft supply box", "other", "new", "archived", "12.50"),
)


@click.command("seed")
@with_appcontext
def seed_command():
    """Add fictional examples once; never erase or replace existing records."""
    if current_app.config["APP_ENV"] == "production":
        raise click.ClickException("Sample data is disabled in production.")
    try:
        existing = []
        for username, email in DEMO_USERS:
            matches = db.session.scalars(select(User).where(or_(
                User.username == username, User.email == email
            ))).all()
            if any(user.username != username or user.email != email for user in matches):
                raise ValueError("A demo identity conflicts with an existing account.")
            existing.extend(matches)
        if existing:
            db.session.rollback()
            click.echo("Demo identities already present; skipped all seed changes.")
            return

        users = []
        for username, email in DEMO_USERS:
            # Random credentials are intentionally discarded. These are data examples,
            # not published accounts that share a known login password.
            user = User(username=username, email=email,
                        password_hash=generate_password_hash(secrets.token_urlsafe(32)))
            db.session.add(user)
            users.append(user)
        for owner, title, category, condition, status, price in DEMO_PRODUCTS:
            db.session.add(Product(
                seller=users[owner], title=title,
                description=f"Fictional demonstration listing: {title}. For project practice only.",
                price=Decimal(price), currency="USD", category=category,
                condition=condition, status=status,
            ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        # Never include raw exception text: it may contain bound private data.
        raise click.ClickException("Seed failed; no changes saved. Check migrations and demo identity conflicts.") from None
    click.echo("Created 3 demo users and 12 demo products.")


def register_commands(application):
    application.cli.add_command(seed_command)
