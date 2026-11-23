"""Stored account identity. Authentication is a separate MM-003 feature."""

import re

from sqlalchemy.orm import validates
from flask_login import UserMixin

from app.extensions import db
from app.models.types import UTCDateTime, bounded_text, utc_now


class User(UserMixin, db.Model):
    __tablename__ = "users"
    __table_args__ = (
        db.UniqueConstraint("username", name="uq_users_username"),
        db.UniqueConstraint("email", name="uq_users_email"),
        db.CheckConstraint("username = lower(trim(username)) AND length(username) BETWEEN 3 AND 30",
                           name="ck_users_username_canonical"),
        db.CheckConstraint("email = lower(trim(email)) AND length(email) BETWEEN 1 AND 254",
                           name="ck_users_email_canonical"),
        db.CheckConstraint("length(password_hash) BETWEEN 1 AND 255", name="ck_users_hash_length"),
        db.CheckConstraint("bio IS NULL OR length(bio) <= 500", name="ck_users_bio_length"),
    )

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(254), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    bio = db.Column(db.String(500), nullable=True)
    enabled = db.Column(db.Boolean, nullable=False, default=True, server_default=db.true())
    personalization = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    created_at = db.Column(UTCDateTime(), nullable=False, default=utc_now)
    updated_at = db.Column(UTCDateTime(), nullable=False, default=utc_now, onupdate=utc_now)
    products = db.relationship("Product", back_populates="seller", passive_deletes="all")

    @property
    def is_active(self):
        return self.enabled

    @validates("username")
    def validate_username(self, key, value):
        value = bounded_text(value, key, 3, 30).lower()
        if re.fullmatch(r"[a-z0-9_-]+", value, flags=re.ASCII) is None:
            raise ValueError("Username may contain letters, numbers, underscores, and hyphens.")
        return value

    @validates("email")
    def validate_email(self, key, value):
        return bounded_text(value, key, 1, 254).lower()

    @validates("password_hash")
    def validate_password_hash(self, key, value):
        # Hash algorithm verification belongs to the authentication service in MM-003.
        return bounded_text(value, key, 1, 255)

    @validates("bio")
    def validate_bio(self, key, value):
        return bounded_text(value, key, 0, 500, optional=True)

    def __repr__(self):
        return f"<User id={self.id} username={self.username!r}>"
