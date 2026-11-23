"""Build a bounded, public-only active-product context for MM-027."""

from decimal import Decimal
import re

from sqlalchemy import func, or_, select

from app.extensions import db
from app.models import Product
from app.models.product import CATEGORIES, CONDITIONS


MAX_CANDIDATES = 60
MAX_MATCHES = 40
MAX_QUERY_TERMS = 12


def _terms(query):
    """Return bounded literal words; punctuation never becomes SQL syntax."""
    values = re.findall(r"[^\W_]{2,40}", query.casefold(), flags=re.UNICODE)
    return list(dict.fromkeys(values))[:MAX_QUERY_TERMS]


def _escape_like(value):
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _public_record(product):
    price = product.price if isinstance(product.price, Decimal) else Decimal(str(product.price))
    return {
        "id": product.id,
        "title": product.title,
        "category": CATEGORIES[product.category],
        "condition": CONDITIONS[product.condition],
        "price": format(price, ".2f"),
        "description": product.description.strip()[:300],
    }


def _append_unique(target, products, maximum=MAX_CANDIDATES):
    known = {product.id for product in target}
    for product in products:
        if product.id not in known:
            target.append(product)
            known.add(product.id)
        if len(target) >= maximum:
            break


def select_shop_catalogue(query):
    """Return at most 60 deterministic active records plus a truncation flag."""
    active = Product.status == "active"
    total = db.session.scalar(select(func.count()).select_from(Product).where(active))
    if total <= MAX_CANDIDATES:
        products = db.session.scalars(
            select(Product).where(active).order_by(Product.id.asc())
        ).all()
        return [_public_record(product) for product in products], False

    chosen = []
    terms = _terms(query)
    if terms:
        clauses = []
        for term in terms:
            literal = f"%{_escape_like(term)}%"
            clauses.extend((
                Product.title.ilike(literal, escape="\\"),
                Product.description.ilike(literal, escape="\\"),
                Product.category.ilike(literal, escape="\\"),
                Product.condition.ilike(literal, escape="\\"),
            ))
        matches = db.session.scalars(
            select(Product).where(active, or_(*clauses)).order_by(
                Product.price.asc(), Product.created_at.desc(), Product.id.asc()
            ).limit(MAX_MATCHES)
        ).all()
        _append_unique(chosen, matches)

    cheapest = db.session.scalars(
        select(Product).where(active).order_by(
            Product.price.asc(), Product.created_at.desc(), Product.id.asc()
        ).limit(MAX_CANDIDATES)
    ).all()
    _append_unique(chosen, cheapest)
    if len(chosen) < MAX_CANDIDATES:
        newest = db.session.scalars(
            select(Product).where(active).order_by(
                Product.created_at.desc(), Product.id.desc()
            ).limit(MAX_CANDIDATES)
        ).all()
        _append_unique(chosen, newest)
    return [_public_record(product) for product in chosen], True
