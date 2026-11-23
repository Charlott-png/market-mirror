"""Persistent user carts and an explicitly non-purchasing checkout demonstration."""

from decimal import Decimal

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import StaleDataError

from app.checkout import (BadCheckoutToken, EmptyCheckout, StaleCheckout,
                          UnavailableCheckout, complete_checkout,
                          make_checkout_token, product_is_eligible,
                          read_checkout_token, existing_order)
from app.extensions import db
from app.marketplace import locked_product, paginate
from app.models import CartItem, Product
from app.security import safe_next


cart = Blueprint("cart", __name__)


def invalidate_cart_count():
    """Forget the request/app-context cache after a cart mutation."""
    g.pop("cart_count", None)
    g.pop("cart_count_user_id", None)


def return_path(value):
    """Use a validated local path, with a cart-specific fallback."""
    if not value:
        return url_for("cart.review")
    checked = safe_next(value)
    if checked == "/dashboard" and value != "/dashboard":
        return url_for("cart.review")
    return checked


def eligible(product):
    return product_is_eligible(product, current_user.id)


def full_rows(lock=False):
    statement = (select(CartItem).options(joinedload(CartItem.product).joinedload(Product.seller))
                 .where(CartItem.user_id == current_user.id)
                 .order_by(CartItem.added_at.desc(), CartItem.product_id.desc()))
    if lock:
        statement = statement.with_for_update()
    return db.session.scalars(statement).unique().all()


def summarize(rows):
    presentations = []
    subtotal = Decimal("0.00")
    unavailable = 0
    for row in rows:
        is_eligible = eligible(row.product)
        if is_eligible:
            subtotal += row.product.price
        else:
            unavailable += 1
        presentations.append({"row": row, "eligible": is_eligible,
                              "product": row.product if is_eligible else None})
    return presentations, subtotal.quantize(Decimal("0.01")), unavailable


def cart_state():
    if len(request.args.getlist("page")) > 1:
        abort(400, description="Supply the page number only once.")
    statement = (select(CartItem).options(joinedload(CartItem.product).joinedload(Product.seller))
                 .where(CartItem.user_id == current_user.id)
                 .order_by(CartItem.added_at.desc(), CartItem.product_id.desc()))
    page = paginate(statement)
    page["cart_items"], _, _ = summarize(page.pop("items"))
    all_items = full_rows()
    _, page["subtotal"], page["unavailable_count"] = summarize(all_items)
    page["can_checkout"] = page["total"] > 0 and page["unavailable_count"] == 0
    page["checkout_token"] = (make_checkout_token(current_user.id, all_items)
                              if page["can_checkout"] else None)
    return page


def render_cart(status=200, checkout_message=None, error_message=None):
    return render_template("cart.html", checkout_message=checkout_message,
                           error_message=error_message, **cart_state()), status


@cart.post("/cart/items/<int:product_id>")
@login_required
def add(product_id):
    product = locked_product(product_id)
    if product is None or product.status == "archived":
        abort(404)
    if not eligible(product):
        abort(400, description="Add an active product offered by another enabled seller.")
    already_present = db.session.get(CartItem, (current_user.id, product_id)) is not None
    if not already_present:
        try:
            db.session.add(CartItem(user_id=current_user.id, product_id=product_id))
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            if db.session.get(CartItem, (current_user.id, product_id)) is None:
                raise
            already_present = True
    if already_present:
        flash("This product is already in your cart.")
    else:
        invalidate_cart_count()
        flash("Product added to your cart.")
    return redirect(return_path(request.form.get("next")))


@cart.post("/cart/items/<int:product_id>/remove")
@login_required
def remove(product_id):
    db.session.execute(delete(CartItem).where(CartItem.user_id == current_user.id,
                                              CartItem.product_id == product_id))
    db.session.commit()
    invalidate_cart_count()
    flash("Product removed from your cart.")
    return redirect(url_for("cart.review"))


@cart.get("/cart")
@login_required
def review():
    return render_cart()


@cart.post("/cart/checkout")
@login_required
def checkout():
    values = request.form.getlist("checkout_token")
    if len(values) != 1 or not values[0]:
        # Preserve the useful MM-019 response for direct empty/unavailable posts.
        # An eligible cart still requires exactly one signed token.
        if not values:
            rows = full_rows()
            _, _, unavailable = summarize(rows)
            if not rows:
                return render_cart(400, error_message=(
                    "Your cart is empty. Add a product before checkout."))
            if unavailable:
                return render_cart(409, error_message=(
                    "Your cart changed. Remove unavailable products before checkout."))
        abort(400, description="Please reopen your cart before checkout.")

    encoded = values[0]
    token = None
    try:
        token = read_checkout_token(encoded, current_user.id)
        prior = existing_order(token)
        if prior is not None:
            db.session.rollback()
            invalidate_cart_count()
            return redirect(url_for("orders.success", order_id=prior.id), code=303)
        order = complete_checkout(current_user.id, encoded)
        invalidate_cart_count()
        return redirect(url_for("orders.success", order_id=order.id), code=303)
    except BadCheckoutToken:
        db.session.rollback()
        abort(400, description="Please reopen your cart before checkout.")
    except EmptyCheckout:
        db.session.rollback()
        return render_cart(400, error_message="Your cart is empty. Add a product before checkout.")
    except (StaleCheckout, UnavailableCheckout):
        db.session.rollback()
        return render_cart(409, error_message=(
            "Your cart changed. Please review the current items and total before checkout."))
    except (IntegrityError, StaleDataError):
        db.session.rollback()
        if token is not None:
            prior = existing_order(token)
            if prior is not None:
                invalidate_cart_count()
                return redirect(url_for("orders.success", order_id=prior.id), code=303)
        return render_cart(409, error_message=(
            "Another buyer changed one of these products. Please review your cart."))
