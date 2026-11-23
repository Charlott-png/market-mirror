"""Small adapters for consistent UTC times and exact money across databases."""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import DateTime, Integer, Numeric
from sqlalchemy.types import TypeDecorator


def utc_now():
    return datetime.now(timezone.utc)


def validated_price(value):
    """Require explicit decimal money; never silently round a seller's price."""
    if not isinstance(value, Decimal):
        raise TypeError("Price must be a Decimal value.")
    if not value.is_finite() or not Decimal("0.01") <= value <= Decimal("9999999.99"):
        raise ValueError("Price must be between 0.01 and 9999999.99.")
    try:
        rounded = value.quantize(Decimal("0.01"))
    except InvalidOperation as error:
        raise ValueError("Price must have at most two decimal places.") from error
    if rounded != value:
        raise ValueError("Price must have at most two decimal places.")
    return rounded


class Money(TypeDecorator):
    """Decimal dollars in Python; integer cents on SQLite; NUMERIC elsewhere."""

    impl = Numeric(10, 2)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "sqlite":
            return dialect.type_descriptor(Integer())
        return dialect.type_descriptor(Numeric(10, 2))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        value = validated_price(value)
        return int(value * 100) if dialect.name == "sqlite" else value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "sqlite":
            return (Decimal(value) / 100).quantize(Decimal("0.01"))
        return Decimal(value).quantize(Decimal("0.01"))


class UTCDateTime(TypeDecorator):
    """Restore UTC information that SQLite's datetime storage does not retain."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Timestamp must include a timezone.")
        return value.astimezone(timezone.utc)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


def bounded_text(value, field, minimum, maximum, optional=False):
    """Normalize optional blanks to NULL and validate visible text length."""
    if value is None and optional:
        return None
    if not isinstance(value, str):
        raise TypeError(f"{field} must be text.")
    value = value.strip()
    if not value and optional:
        return None
    if not minimum <= len(value) <= maximum:
        raise ValueError(f"{field} must contain {minimum} to {maximum} characters.")
    return value
