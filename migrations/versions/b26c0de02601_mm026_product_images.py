"""MM-026 ordered product galleries.

Revision ID: b26c0de02601
Revises: a25c0de02501
Create Date: 2026-11-07
"""

from alembic import op
import sqlalchemy as sa


revision = "b26c0de02601"
down_revision = "a25c0de02501"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    duplicate = bind.execute(sa.text(
        "SELECT image_filename FROM products WHERE image_filename IS NOT NULL "
        "GROUP BY image_filename HAVING count(*) > 1 LIMIT 1")).first()
    if duplicate is not None:
        raise RuntimeError("Resolve duplicate legacy product image references before MM-026 migration.")
    op.create_table(
        "product_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(trim(filename)) BETWEEN 1 AND 255",
                           name="ck_product_images_filename_length"),
        sa.CheckConstraint("position BETWEEN 0 AND 4", name="ck_product_images_position"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("filename", name="uq_product_images_filename"),
        sa.UniqueConstraint("product_id", "position",
                            name="uq_product_images_product_position"),
    )
    op.create_index("ix_product_images_product_position", "product_images",
                    ["product_id", "position"], unique=False)
    bind.execute(sa.text(
        "INSERT INTO product_images (product_id, filename, position, created_at) "
        "SELECT id, image_filename, 0, created_at FROM products "
        "WHERE image_filename IS NOT NULL"))


def downgrade():
    op.drop_index("ix_product_images_product_position", table_name="product_images")
    op.drop_table("product_images")
