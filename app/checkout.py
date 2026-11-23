"""Safe signed checkout tokens and the atomic MM-025 purchase service."""

from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json
import secrets

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select, text
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import CartItem, Order, OrderItem, Product


TOKEN_SALT = "market-mirror-mm025-checkout-v1"
MAX_ENCODED_TOKEN_LENGTH = 1000


class CheckoutProblem(Exception):
    """Base class for checkout results that are safe to explain to a buyer."""


class BadCheckoutToken(CheckoutProblem):
    pass


class EmptyCheckout(CheckoutProblem):
    pass


class StaleCheckout(CheckoutProblem):
    pass


class UnavailableCheckout(CheckoutProblem):
    pass


@dataclass(frozen=True)
class CheckoutToken:
    buyer_id: int
    nonce: str
    fingerprint: str
    expired: bool


def product_is_eligible(product, buyer_id):
    """Return whether one listing can be purchased by this buyer right now."""
    return bool(product and product.status == "active" and product.seller_id != buyer_id
                and product.seller and product.seller.enabled)


def cart_fingerprint(rows):
    """Hash the complete cart state without putting its private details in a token."""
    values = sorted((row.product_id, row.product.version,
                     format(row.product.price, ".2f"), row.product.currency)
                    for row in rows)
    canonical = json.dumps(values, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


def _serializer():
    return URLSafeTimedSerializer(current_app.secret_key, salt=TOKEN_SALT)


def make_checkout_token(buyer_id, rows):
    payload = {
        "buyer_id": buyer_id,
        "nonce": secrets.token_urlsafe(24),
        "fingerprint": cart_fingerprint(rows),
    }
    return _serializer().dumps(payload)


def read_checkout_token(encoded, buyer_id):
    """Verify signature/shape/owner and report age without trusting form data."""
    if not isinstance(encoded, str) or not encoded or len(encoded) > MAX_ENCODED_TOKEN_LENGTH:
        raise BadCheckoutToken()
    try:
        # First verify the signature without an age limit. This allows a completed
        # order to recover from a lost response even after the form has expired.
        payload = _serializer().loads(encoded)
    except BadSignature as error:
        raise BadCheckoutToken() from error
    if not isinstance(payload, dict) or set(payload) != {"buyer_id", "nonce", "fingerprint"}:
        raise BadCheckoutToken()
    token_buyer = payload.get("buyer_id")
    nonce = payload.get("nonce")
    fingerprint = payload.get("fingerprint")
    if (type(token_buyer) is not int or token_buyer != buyer_id or
            not isinstance(nonce, str) or not 20 <= len(nonce) <= 64 or
            not isinstance(fingerprint, str) or len(fingerprint) != 64 or
            any(character not in "0123456789abcdef" for character in fingerprint)):
        raise BadCheckoutToken()
    try:
        _serializer().loads(encoded, max_age=current_app.config["CHECKOUT_TOKEN_MAX_AGE"])
        expired = False
    except SignatureExpired:
        expired = True
    except BadSignature as error:
        raise BadCheckoutToken() from error
    return CheckoutToken(token_buyer, nonce, fingerprint, expired)


def existing_order(token):
    return db.session.scalar(select(Order).where(
        Order.buyer_id == token.buyer_id, Order.checkout_nonce == token.nonce))


def lock_checkout_rows(buyer_id):
    """Reload the complete cart under write protection in deterministic order."""
    id_statement = (select(CartItem.product_id)
                    .where(CartItem.user_id == buyer_id)
                    .order_by(CartItem.product_id))
    if db.engine.dialect.name != "sqlite":
        id_statement = id_statement.with_for_update()
    product_ids = list(db.session.scalars(id_statement))
    if db.engine.dialect.name == "sqlite":
        for product_id in product_ids:
            db.session.execute(text("UPDATE products SET version = version WHERE id = :id"),
                               {"id": product_id})
    elif product_ids:
        list(db.session.scalars(select(Product).where(Product.id.in_(product_ids))
             .order_by(Product.id).with_for_update().execution_options(populate_existing=True)))

    statement = (select(CartItem)
        .options(joinedload(CartItem.product).joinedload(Product.seller))
        .where(CartItem.user_id == buyer_id)
        .order_by(CartItem.product_id)
        .execution_options(populate_existing=True))
    return db.session.scalars(statement).unique().all()


def complete_checkout(buyer_id, encoded_token):
    """Create one complete order, or raise before any partial state can commit."""
    token = read_checkout_token(encoded_token, buyer_id)
    prior = existing_order(token)
    if prior is not None:
        db.session.rollback()
        return prior
    if token.expired:
        raise StaleCheckout()

    rows = lock_checkout_rows(buyer_id)
    # A same-token request may have waited for the first request's product lock.
    # Recheck after that wait so a double-click reaches the completed receipt
    # instead of seeing the now-empty cart as a new checkout.
    prior = existing_order(token)
    if prior is not None:
        db.session.rollback()
        return prior
    if not rows:
        raise EmptyCheckout()
    if any(not product_is_eligible(row.product, buyer_id) for row in rows):
        raise UnavailableCheckout()
    if cart_fingerprint(rows) != token.fingerprint:
        raise StaleCheckout()

    total = sum((row.product.price for row in rows), Decimal("0.00")).quantize(Decimal("0.01"))
    order = Order(buyer_id=buyer_id, status="completed", total_amount=total,
                  currency="USD", checkout_nonce=token.nonce)
    db.session.add(order)
    db.session.flush()
    for row in rows:
        product = row.product
        order.items.append(OrderItem(product_id=product.id, seller_id=product.seller_id,
            product_title=product.title, seller_username=product.seller.username,
            unit_price=product.price, currency=product.currency))
        product.status = "sold"
        db.session.delete(row)
    db.session.flush()
    db.session.commit()
    return order

