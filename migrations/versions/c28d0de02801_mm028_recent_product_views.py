"""MM-028 bounded recently viewed product history.

Revision ID: c28d0de02801
Revises: b26c0de02601
Create Date: 2026-11-07
"""

from alembic import op
import sqlalchemy as sa


revision = "c28d0de02801"
down_revision = "b26c0de02601"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "recent_product_views",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "product_id"),
    )
    op.create_index("ix_recent_product_views_user_viewed_at",
                    "recent_product_views", ["user_id", "viewed_at"],
                    unique=False)


def downgrade():
    op.drop_index("ix_recent_product_views_user_viewed_at",
                  table_name="recent_product_views")
    op.drop_table("recent_product_views")
