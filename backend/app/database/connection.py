"""
MongoDB connection management.

Usage inside the app context:
    from app.database.connection import get_db
    db = get_db()
    db.users.find_one({"email": "..."})
"""
from __future__ import annotations

import logging
from typing import Optional

from pymongo import MongoClient, ASCENDING
from pymongo.database import Database

logger = logging.getLogger(__name__)

_client: Optional[MongoClient] = None
_db: Optional[Database] = None


def init_db(mongo_uri: str, db_name: str) -> None:
    """
    Initialise the MongoDB connection and create required indexes.
    Called once from create_app().
    """
    global _client, _db

    _client = MongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
    )
    _db = _client[db_name]

    _create_indexes(_db)
    logger.info("MongoDB connected — database: %s", db_name)


def get_db() -> Database:
    """Return the active database instance. Must be called after init_db()."""
    if _db is None:
        raise RuntimeError(
            "Database not initialised. Call init_db() inside create_app() first."
        )
    return _db


def close_db() -> None:
    """Close the MongoClient connection (useful in tests)."""
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None


# ──────────────────────────────────────────────────────────────────────────────
# Index definitions
# ──────────────────────────────────────────────────────────────────────────────

def _create_indexes(db: Database) -> None:
    """
    Idempotent index creation.  Indexes are named so they can be inspected
    and dropped individually without touching others.
    """

    # users — unique email is the primary lookup key
    db.users.create_index(
        [("email", ASCENDING)],
        unique=True,
        name="users_email_unique",
    )

    # users — fast lookup by userId (UUID string exposed in API)
    db.users.create_index(
        [("userId", ASCENDING)],
        unique=True,
        name="users_userId_unique",
    )

    # Future: quote_history — fast lookup by owner
    # db.quotes.create_index([("userId", ASCENDING)], name="quotes_userId")

    logger.debug("MongoDB indexes verified / created.")
