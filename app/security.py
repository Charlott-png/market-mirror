"""Clock injection, atomic persistent throttles, and safe session handling."""

import hashlib
import hmac
import time
import uuid
import logging

from flask import abort, current_app, make_response, request, session, g
from flask_login import current_user, logout_user
from sqlalchemy import case

from app.extensions import db, login_manager
from app.models import RateLimit, User


def now():
    return current_app.config.get("CLOCK", time.time)()


def throttle_key(scope, identity):
    secret = current_app.secret_key.encode()
    return hmac.new(secret, f"{scope}:{identity}".encode(), hashlib.sha256).hexdigest()


def too_many(expires_at):
    response = make_response("Too many attempts. Please try again later.", 429)
    response.headers["Retry-After"] = str(max(1, int(expires_at - now()) + 1))
    abort(response)


def check_limit(scope, identity, limit):
    row = db.session.get(RateLimit, throttle_key(scope, identity))
    if row and row.expires_at > now() and row.count >= limit:
        too_many(row.expires_at)


def consume_limit(scope, identity, limit, seconds):
    """One atomic upsert prevents simultaneous requests bypassing counters."""
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    insert = pg_insert if db.engine.dialect.name == "postgresql" else sqlite_insert
    timestamp = now()
    deadline = (int(timestamp) // seconds + 1) * seconds
    key = throttle_key(scope, identity)
    statement = insert(RateLimit).values(key=key, count=1, expires_at=deadline)
    statement = statement.on_conflict_do_update(index_elements=[RateLimit.key], set_={
        "count": case((RateLimit.expires_at <= timestamp, 1), else_=RateLimit.count + 1),
        "expires_at": case((RateLimit.expires_at <= timestamp, deadline), else_=RateLimit.expires_at),
    }).returning(RateLimit.count, RateLimit.expires_at)
    count, expires = db.session.execute(statement).one()
    db.session.commit()
    if count > limit:
        too_many(expires)


def safe_next(value):
    return value if (value and value.startswith("/") and not value.startswith("//")
                     and "\\" not in value and not any(ord(c) < 32 for c in value)) else "/dashboard"


@login_manager.user_loader
def load_user(user_id):
    try:
        user = db.session.get(User, int(user_id))
        return user if user and user.enabled else None
    except (ValueError, TypeError):
        return None


def initialize_security(application):
    # Flask applications created repeatedly by tests share the named ``app``
    # logger. Reset its routing flags for every application so another runtime
    # or earlier app instance cannot silently disable request audit records.
    application.logger.disabled = False
    application.logger.propagate = True
    application.logger.setLevel(logging.INFO)

    @application.before_request
    def start_request():
        # Never accept a client-supplied identifier or log URLs/query strings.
        g.request_id = uuid.uuid4().hex
        g.request_started = time.perf_counter()

    @application.before_request
    def expire_session():
        g.pop("_login_user", None)
        if "_user_id" in session:
            started = session.get("login_at", 0)
            if not isinstance(started, (float, int)) or now() - started >= 8 * 3600:
                logout_user()
                session.clear()

    @application.after_request
    def secure_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        # ``blob:`` is limited to images so the Sell form can display a local
        # thumbnail without uploading the selected file before submission.
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data: blob:; style-src 'self'; script-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'self'"
        if "_user_id" in session or request.path.startswith(("/auth", "/media")):
            response.headers["Cache-Control"] = "private, no-store"
        if application.config["APP_ENV"] == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        identifier = g.get("request_id", uuid.uuid4().hex)
        response.headers["X-Request-ID"] = identifier
        elapsed = (time.perf_counter() - g.get("request_started", time.perf_counter())) * 1000
        application.logger.info("request_complete id=%s status=%d duration_ms=%.1f", identifier, response.status_code, max(0, elapsed))
        return response
