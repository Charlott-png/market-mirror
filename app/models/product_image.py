"""Ordered normalized photos belonging to one product."""

from sqlalchemy.orm import validates

from app.extensions import db
from app.images import FILENAME
from app.models.types import UTCDateTime, bounded_text, utc_now


class ProductImage(db.Model):
    __tablename__ = "product_images"
    __table_args__ = (
        db.UniqueConstraint("product_id", "position", name="uq_product_images_product_position"),
        db.UniqueConstraint("filename", name="uq_product_images_filename"),
        db.CheckConstraint("position BETWEEN 0 AND 4", name="ck_product_images_position"),
        db.CheckConstraint("length(trim(filename)) BETWEEN 1 AND 255",
                           name="ck_product_images_filename_length"),
        db.Index("ix_product_images_product_position", "product_id", "position"),
    )
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"),
                           nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    created_at = db.Column(UTCDateTime(), nullable=False, default=utc_now)
    product = db.relationship("Product", back_populates="gallery_images")

    @validates("filename")
    def validate_filename(self, key, value):
        value = bounded_text(value, key, 1, 255)
        if FILENAME.fullmatch(value) is None:
            raise ValueError("Image filename is not a normalized JPEG reference.")
        return value

    @validates("position")
    def validate_position(self, key, value):
        if type(value) is not int or not 0 <= value <= 4:
            raise ValueError("Image position must be from 0 to 4.")
        return value
