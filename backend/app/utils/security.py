"""
Security utilities: password hashing and JWT token management.

Design decisions
----------------
* bcrypt work factor is read from Config so it can be lowered in tests.
* Access tokens are signed with JWT_SECRET; refresh tokens use a separate
  JWT_REFRESH_SECRET so a compromised access token cannot forge a refresh.
* Refresh token payloads include `type: "refresh"` to prevent accidentally
  accepting a refresh token on an access-protected endpoint and vice versa.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Password helpers
# ──────────────────────────────────────────────────────────────────────────────

def hash_password(plain: str, rounds: int = 12) -> str:
    """Return a bcrypt hash string for *plain*."""
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches the stored bcrypt *hashed* value."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ──────────────────────────────────────────────────────────────────────────────
# JWT helpers
# ──────────────────────────────────────────────────────────────────────────────

def create_access_token(
    user_id: str,
    role: str,
    secret: str,
    expiry_minutes: int = 15,
) -> str:
    """Create a short-lived JWT access token."""
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=expiry_minutes),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def create_refresh_token(
    user_id: str,
    secret: str,
    expiry_days: int = 7,
) -> str:
    """Create a long-lived JWT refresh token signed with a separate secret."""
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=expiry_days),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(token: str, secret: str) -> Optional[dict]:
    """
    Decode and validate a JWT.

    Returns the payload dict on success, or None if the token is invalid,
    expired, or tampered with.  Exceptions are caught and logged.
    """
    try:
        return jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        logger.debug("Token expired.")
        return None
    except jwt.InvalidTokenError as exc:
        logger.debug("Invalid token: %s", exc)
        return None


def hash_token(raw_token: str, rounds: int = 12) -> str:
    """Bcrypt-hash a raw token for safe storage (used for refresh tokens in DB)."""
    return hash_password(raw_token, rounds=rounds)


def verify_token_hash(raw_token: str, stored_hash: str) -> bool:
    """Verify a raw token against a stored bcrypt hash."""
    return verify_password(raw_token, stored_hash)
