"""Marketplace relations. Unique constraints protect against competing requests."""

from app.extensions import db
from app.models.types import UTCDateTime, utc_now


class RateLimit(db.Model):
    __tablename__ = "rate_limits"
    key = db.Column(db.String(64), primary_key=True)
    count = db.Column(db.Integer, nullable=False)
    expires_at = db.Column(db.Float, nullable=False, index=True)


class ListingSubmission(db.Model):
    __tablename__ = "listing_submissions"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True)
    token = db.Column(db.String(100), primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)


class Conversation(db.Model):
    __tablename__ = "conversations"
    __table_args__ = (
        db.UniqueConstraint("product_id", "buyer_id", name="uq_conversation_product_buyer"),
        db.CheckConstraint("buyer_id <> seller_id", name="ck_conversation_distinct_people"),
    )
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at = db.Column(UTCDateTime(), nullable=False, default=utc_now)
    product = db.relationship("Product")


class Message(db.Model):
    __tablename__ = "messages"
    __table_args__ = (
        db.UniqueConstraint("sender_id", "request_token", name="uq_message_sender_token"),
        db.CheckConstraint("length(trim(body)) BETWEEN 1 AND 2000", name="ck_message_body"),
    )
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id", ondelete="RESTRICT"), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    body = db.Column(db.String(2000), nullable=False)
    request_token = db.Column(db.String(100), nullable=False)
    created_at = db.Column(UTCDateTime(), nullable=False, default=utc_now)
    sender = db.relationship("User")


class ReadMarker(db.Model):
    __tablename__ = "read_markers"
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id", ondelete="RESTRICT"), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True)
    last_read_message_id = db.Column(db.Integer, db.ForeignKey("messages.id", ondelete="RESTRICT"), nullable=False)


class SavedProduct(db.Model):
    __tablename__ = "saved_products"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="RESTRICT"), primary_key=True)
    created_at = db.Column(UTCDateTime(), nullable=False, default=utc_now)
    product = db.relationship("Product")


class CartItem(db.Model):
    """One user's interest in one marketplace listing; this is not a reservation."""

    __tablename__ = "cart_items"
    __table_args__ = (
        db.Index("ix_cart_items_product_id", "product_id"),
        db.Index("ix_cart_items_user_added_at", "user_id", "added_at"),
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="RESTRICT"), primary_key=True)
    added_at = db.Column(UTCDateTime(), nullable=False, default=utc_now)
    product = db.relationship("Product")


class InteractionEvent(db.Model):
    __tablename__ = "interaction_events"
    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", "kind", "window", name="uq_event_window"),
        db.CheckConstraint("kind IN ('view', 'save', 'contact')", name="ck_event_kind"),
    )
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    kind = db.Column(db.String(10), nullable=False)
    window = db.Column(db.Integer, nullable=False)
    created_at = db.Column(UTCDateTime(), nullable=False, default=utc_now, index=True)


class RecentProductView(db.Model):
    """One user's bounded, user-facing product history entry."""

    __tablename__ = "recent_product_views"
    __table_args__ = (
        db.Index("ix_recent_product_views_user_viewed_at", "user_id", "viewed_at"),
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"),
                        primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"),
                           primary_key=True)
    viewed_at = db.Column(UTCDateTime(), nullable=False, default=utc_now)
    product = db.relationship("Product")
