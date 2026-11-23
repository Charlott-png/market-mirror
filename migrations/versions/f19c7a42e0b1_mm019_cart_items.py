"""MM-019 persistent shopping-cart pairs.

Revision ID: f19c7a42e0b1
Revises: d88e8d30439f
Create Date: 2026-11-02
"""

from alembic import op
import sqlalchemy as sa


revision = "f19c7a42e0b1"
down_revision = "d88e8d30439f"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cart_items",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("user_id", "product_id"),
    )
    op.create_index("ix_cart_items_product_id", "cart_items", ["product_id"], unique=False)
    op.create_index("ix_cart_items_user_added_at", "cart_items", ["user_id", "added_at"], unique=False)


def downgrade():
    op.drop_index("ix_cart_items_user_added_at", table_name="cart_items")
    op.drop_index("ix_cart_items_product_id", table_name="cart_items")
    op.drop_table("cart_items")
