"""MM-002 tests for the User database model."""

import pytest


def test_valid_user_persists_with_normalized_identity(db_app):
    """TEST-USER-001 and TEST-USER-002: valid identity persists normalized."""
    from app.extensions import db
    from app.models import User

    with db_app.app_context():
        user = User(
            username="  Student-One  ",
            email="  STUDENT.ONE@EXAMPLE.TEST  ",
            password_hash="secure-test-hash",
        )
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        created_at = user.created_at

        db.session.remove()
        stored = db.session.get(User, user_id)

        assert stored.username == "student-one"
        assert stored.email == "student.one@example.test"
        assert stored.created_at is not None
        assert stored.updated_at is not None
        assert stored.created_at == created_at


@pytest.mark.parametrize(
    ("field", "value", "is_valid"),
    [
        ("username", "ab", False),
        ("username", "abc", True),
        ("username", "a" * 30, True),
        ("username", "a" * 31, False),
        ("username", "student name", False),
        ("username", "student_name-2", True),
        ("email", "", False),
        ("email", f"{'a' * 64}@{'b' * 63}.{'c' * 63}.{'d' * 61}", True),
        ("email", f"x@{'a' * 253}", False),
        ("password_hash", "", False),
        ("password_hash", "h" * 255, True),
        ("password_hash", "h" * 256, False),
        ("bio", "b" * 500, True),
        ("bio", "b" * 501, False),
    ],
)
def test_user_field_boundaries(db_session, field, value, is_valid):
    """TEST-USER-003: model validation enforces approved boundaries."""
    from app.models import User

    values = {
        "username": "valid-user",
        "email": "valid@example.test",
        "password_hash": "secure-test-hash",
    }
    values[field] = value

    if is_valid:
        user = User(**values)
        db_session.add(user)
        db_session.commit()
        assert user.id is not None
    else:
        with pytest.raises((ValueError, TypeError)):
            User(**values)
        db_session.rollback()


@pytest.mark.parametrize(
    "duplicate_values",
    [
        {"username": "ORIGINAL", "email": "different@example.test"},
        {"username": "different", "email": " ORIGINAL@EXAMPLE.TEST "},
    ],
)
def test_duplicate_normalized_identity_is_rejected(
    db_session, user_factory, duplicate_values
):
    """TEST-USER-004 / AC-DB-004: database uniqueness is authoritative."""
    from app.models import User
    from sqlalchemy.exc import IntegrityError

    original = user_factory(username="original", email="original@example.test")
    duplicate = User(password_hash="another-secure-hash", **duplicate_values)
    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()
    assert db_session.get(User, original.id).username == "original"

    valid = User(
        username="after-rollback",
        email="after-rollback@example.test",
        password_hash="secure-test-hash",
    )
    db_session.add(valid)
    db_session.commit()
    assert valid.id is not None


def test_user_representation_hides_email_and_password_hash(db_session):
    """TEST-USER-005: debugging text never exposes private identity data."""
    from app.models import User

    user = User(
        username="safe-user",
        email="private-canary@example.test",
        password_hash="secret-hash-canary",
    )
    db_session.add(user)
    db_session.flush()

    representation = repr(user)

    assert "safe-user" in representation
    assert "private-canary@example.test" not in representation
    assert "secret-hash-canary" not in representation
