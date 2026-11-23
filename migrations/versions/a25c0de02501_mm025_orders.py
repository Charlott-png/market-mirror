"""MM-025 completed orders and receipt snapshots.

Revision ID: a25c0de02501
Revises: f19c7a42e0b1
Create Date: 2026-11-06
"""

from alembic import op
import sqlalchemy as sa


revision = "a25c0de02501"
down_revision = "f19c7a42e0b1"
branch_labels = None
depends_on = None


def upgrade():
    sqlite = op.get_context().dialect.name == "sqlite"
    money_type = sa.Integer() if sqlite else sa.Numeric(10, 2)
    order_money_check = sa.CheckConstraint(
        "typeof(total_amount) = 'integer' AND total_amount BETWEEN 1 AND 999999999" if sqlite
        else "total_amount BETWEEN 0.01 AND 9999999.99",
        name="ck_orders_total_cents" if sqlite else "ck_orders_total_decimal")
    item_money_check = sa.CheckConstraint(
        "typeof(unit_price) = 'integer' AND unit_price BETWEEN 1 AND 999999999" if sqlite
        else "unit_price BETWEEN 0.01 AND 9999999.99",
        name="ck_order_items_price_cents" if sqlite else "ck_order_items_price_decimal")

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("buyer_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="completed", nullable=False),
        sa.Column("total_amount", money_type, nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.Column("checkout_nonce", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status = 'completed'", name="ck_orders_status"),
        sa.CheckConstraint("currency = 'USD'", name="ck_orders_currency"),
        sa.CheckConstraint("length(checkout_nonce) BETWEEN 20 AND 64",
                           name="ck_orders_nonce_length"),
        order_money_check,
        sa.ForeignKeyConstraint(["buyer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("buyer_id", "checkout_nonce", name="uq_orders_buyer_nonce"),
    )
    op.create_index("ix_orders_buyer_id", "orders", ["buyer_id"], unique=False)

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("seller_id", sa.Integer(), nullable=False),
        sa.Column("product_title", sa.String(length=120), nullable=False),
        sa.Column("seller_username", sa.String(length=30), nullable=False),
        sa.Column("unit_price", money_type, nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="USD", nullable=False),
        sa.CheckConstraint("length(trim(product_title)) BETWEEN 3 AND 120",
                           name="ck_order_items_title_length"),
        sa.CheckConstraint(
            "seller_username = lower(trim(seller_username)) AND "
            "length(seller_username) BETWEEN 3 AND 30",
            name="ck_order_items_seller_username"),
        sa.CheckConstraint("currency = 'USD'", name="ck_order_items_currency"),
        item_money_check,
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["seller_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", name="uq_order_items_product"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"], unique=False)
    op.create_index("ix_order_items_product_id", "order_items", ["product_id"], unique=False)
    op.create_index("ix_order_items_seller_id", "order_items", ["seller_id"], unique=False)


def downgrade():
    op.drop_index("ix_order_items_seller_id", table_name="order_items")
    op.drop_index("ix_order_items_product_id", table_name="order_items")
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_buyer_id", table_name="orders")
    op.drop_table("orders")
