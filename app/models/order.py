"""Completed local orders and immutable receipt snapshots."""

import re

from sqlalchemy.orm import validates

from app.extensions import db
from app.models.types import Money, UTCDateTime, bounded_text, utc_now, validated_price


class Order(db.Model):
    """One completed checkout belonging to one buyer."""

    __tablename__ = "orders"
    __table_args__ = (
        db.UniqueConstraint("buyer_id", "checkout_nonce", name="uq_orders_buyer_nonce"),
        db.CheckConstraint("status = 'completed'", name="ck_orders_status"),
        db.CheckConstraint("currency = 'USD'", name="ck_orders_currency"),
        db.CheckConstraint("length(checkout_nonce) BETWEEN 20 AND 64",
                           name="ck_orders_nonce_length"),
        db.CheckConstraint("typeof(total_amount) = 'integer' AND total_amount BETWEEN 1 AND 999999999",
                           name="ck_orders_total_cents").ddl_if(dialect="sqlite"),
        db.CheckConstraint("total_amount BETWEEN 0.01 AND 9999999.99",
                           name="ck_orders_total_decimal").ddl_if(dialect="postgresql"),
    )

    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"),
                         nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="completed",
                       server_default="completed")
    total_amount = db.Column(Money(), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="USD", server_default="USD")
    checkout_nonce = db.Column(db.String(64), nullable=False)
    created_at = db.Column(UTCDateTime(), nullable=False, default=utc_now)

    buyer = db.relationship("User", foreign_keys=[buyer_id])
    items = db.relationship("OrderItem", back_populates="order",
                            cascade="all, delete-orphan", passive_deletes=True,
                            order_by="OrderItem.id")

    @validates("status", "currency")
    def validate_choice(self, key, value):
        expected = {"status": "completed", "currency": "USD"}[key]
        if value != expected:
            raise ValueError(f"Unsupported order {key}.")
        return value

    @validates("total_amount")
    def validate_total(self, key, value):
        return validated_price(value)

    @validates("checkout_nonce")
    def validate_nonce(self, key, value):
        return bounded_text(value, key, 20, 64)


class OrderItem(db.Model):
    """Receipt data for one unique marketplace listing."""

    __tablename__ = "order_items"
    __table_args__ = (
        db.Index("ix_order_items_product_id", "product_id"),
        db.UniqueConstraint("product_id", name="uq_order_items_product"),
        db.CheckConstraint("length(trim(product_title)) BETWEEN 3 AND 120",
                           name="ck_order_items_title_length"),
        db.CheckConstraint(
            "seller_username = lower(trim(seller_username)) AND "
            "length(seller_username) BETWEEN 3 AND 30",
            name="ck_order_items_seller_username"),
        db.CheckConstraint("currency = 'USD'", name="ck_order_items_currency"),
        db.CheckConstraint("typeof(unit_price) = 'integer' AND unit_price BETWEEN 1 AND 999999999",
                           name="ck_order_items_price_cents").ddl_if(dialect="sqlite"),
        db.CheckConstraint("unit_price BETWEEN 0.01 AND 9999999.99",
                           name="ck_order_items_price_decimal").ddl_if(dialect="postgresql"),
    )

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="RESTRICT"),
                           nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"),
                          nullable=False, index=True)
    product_title = db.Column(db.String(120), nullable=False)
    seller_username = db.Column(db.String(30), nullable=False)
    unit_price = db.Column(Money(), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="USD", server_default="USD")

    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product")
    seller = db.relationship("User", foreign_keys=[seller_id])

    @validates("product_title")
    def validate_title(self, key, value):
        return bounded_text(value, key, 3, 120)

    @validates("seller_username")
    def validate_seller_username(self, key, value):
        value = bounded_text(value, key, 3, 30).lower()
        if re.fullmatch(r"[a-z0-9_-]+", value, flags=re.ASCII) is None:
            raise ValueError("Seller username snapshot is not canonical.")
        return value

    @validates("unit_price")
    def validate_unit_price(self, key, value):
        return validated_price(value)

    @validates("currency")
    def validate_currency(self, key, value):
        if value != "USD":
            raise ValueError("Unsupported order item currency.")
        return value

