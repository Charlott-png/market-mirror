"""Bounded private recent-product history for MM-028."""

from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import Product, RecentProductView, User
from app.security import now


MAX_RECENT_PRODUCTS = 5


def record_recent_view(user_id, product_id):
    """Insert/refresh one active view and prune this user to five rows."""
    if db.engine.dialect.name == "sqlite":
        db.session.execute(text("UPDATE users SET id = id WHERE id = :id"),
                           {"id": user_id})
    user = db.session.scalar(select(User).where(User.id == user_id).with_for_update())
    product = db.session.scalar(select(Product).where(
        Product.id == product_id, Product.status == "active"))
    if user is None or product is None:
        return False

    timestamp = datetime.fromtimestamp(now(), timezone.utc)
    row = db.session.get(RecentProductView, (user_id, product_id))
    if row is None:
        db.session.add(RecentProductView(
            user_id=user_id, product_id=product_id, viewed_at=timestamp))
    else:
        row.viewed_at = timestamp
    db.session.flush()

    ordered = db.session.scalars(select(RecentProductView).where(
        RecentProductView.user_id == user_id).order_by(
            RecentProductView.viewed_at.desc(),
            RecentProductView.product_id.desc())).all()
    for obsolete in ordered[MAX_RECENT_PRODUCTS:]:
        db.session.delete(obsolete)
    return True


def recent_products(user_id):
    """Return at most five current active products in private history order."""
    statement = (select(Product)
        .join(RecentProductView, RecentProductView.product_id == Product.id)
        .options(joinedload(Product.seller))
        .where(RecentProductView.user_id == user_id,
               Product.status == "active")
        .order_by(RecentProductView.viewed_at.desc(),
                  RecentProductView.product_id.desc())
        .limit(MAX_RECENT_PRODUCTS))
    return db.session.scalars(statement).all()
