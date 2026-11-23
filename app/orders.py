"""Private, read-only completed-order pages."""

from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import Order


orders = Blueprint("orders", __name__)


@orders.get("/orders/<int:order_id>/success")
@login_required
def success(order_id):
    order = db.session.scalar(select(Order).options(selectinload(Order.items)).where(
        Order.id == order_id, Order.buyer_id == current_user.id))
    if order is None:
        abort(404)
    return render_template("order_success.html", order=order)

