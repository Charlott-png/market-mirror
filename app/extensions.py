"""Unbound extensions can be reused by independent application instances."""

import sqlite3

from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
csrf = CSRFProtect()


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(connection, connection_record):
    """SQLite requires foreign-key enforcement on EVERY new connection."""
    if isinstance(connection, sqlite3.Connection):
        # Python 3.12+ may have autocommit=False; PRAGMA must run outside a transaction.
        previous = getattr(connection, "autocommit", None)
        if previous is not None:
            connection.autocommit = True
        try:
            cursor = connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys=ON")
            finally:
                cursor.close()
        finally:
            if previous is not None:
                connection.autocommit = previous
