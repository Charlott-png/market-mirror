"""Product data, approved choices, and ownership constraints."""

from sqlalchemy.orm import validates

from app.extensions import db
from app.models.types import Money, UTCDateTime, bounded_text, utc_now, validated_price

CATEGORIES = {
    "electronics": "Electronics", "home_garden": "Home & Garden", "clothing": "Clothing",
    "books_media": "Books & Media", "sports_outdoors": "Sports & Outdoors",
    "toys_games": "Toys & Games", "other": "Other",
}
CONDITIONS = {"new": "New", "like_new": "Like New", "good": "Good", "fair": "Fair"}
STATUSES = {"active": "Active", "sold": "Sold", "archived": "Archived"}
CURRENCIES = {"USD": "US Dollar"}


class Product(db.Model):
    __tablename__ = "products"
    __table_args__ = (
        db.CheckConstraint("length(trim(title)) BETWEEN 3 AND 120", name="ck_products_title_length"),
        db.CheckConstraint("length(trim(description)) BETWEEN 10 AND 5000", name="ck_products_description_length"),
        db.CheckConstraint("image_filename IS NULL OR length(image_filename) <= 255", name="ck_products_image_length"),
        db.CheckConstraint("currency = 'USD'", name="ck_products_currency"),
        db.CheckConstraint("category IN (" + ", ".join(repr(key) for key in CATEGORIES) + ")",
                           name="ck_products_category"),
        db.CheckConstraint("condition IN (" + ", ".join(repr(key) for key in CONDITIONS) + ")",
                           name="ck_products_condition"),
        db.CheckConstraint("status IN (" + ", ".join(repr(key) for key in STATUSES) + ")",
                           name="ck_products_status"),
        db.CheckConstraint("typeof(price) = 'integer' AND price BETWEEN 1 AND 999999999",
                           name="ck_products_price_cents").ddl_if(dialect="sqlite"),
        db.CheckConstraint("price BETWEEN 0.01 AND 9999999.99",
                           name="ck_products_price_decimal").ddl_if(dialect="postgresql"),
    )

    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.Integer, nullable=False, default=1, server_default="1")
    __mapper_args__ = {"version_id_col": version}
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT",
                          name="fk_products_seller"), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(Money(), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="USD")
    category = db.Column(db.String(40), nullable=False, index=True)
    condition = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="active", server_default="active", index=True)
    image_filename = db.Column(db.String(255), nullable=True)
    created_at = db.Column(UTCDateTime(), nullable=False, default=utc_now, index=True)
    updated_at = db.Column(UTCDateTime(), nullable=False, default=utc_now, onupdate=utc_now)
    seller = db.relationship("User", back_populates="products")
    gallery_images = db.relationship("ProductImage", back_populates="product",
        cascade="all, delete-orphan", passive_deletes=True,
        order_by="ProductImage.position")

    @validates("title", "description", "image_filename")
    def validate_text(self, key, value):
        minimum, maximum = {"title": (3, 120), "description": (10, 5000),
                            "image_filename": (0, 255)}[key]
        return bounded_text(value, key, minimum, maximum, optional=key == "image_filename")

    @validates("price")
    def validate_price(self, key, value):
        return validated_price(value)

    @validates("category", "condition", "status", "currency")
    def validate_choice(self, key, value):
        choices = {"category": CATEGORIES, "condition": CONDITIONS,
                   "status": STATUSES, "currency": CURRENCIES}[key]
        if not isinstance(value, str) or value not in choices:
            raise ValueError(f"Unsupported {key}.")
        return value

    def __repr__(self):
        title = (self.title or "")[:50]
        return f"<Product id={self.id} title={title!r} status={self.status!r}>"
