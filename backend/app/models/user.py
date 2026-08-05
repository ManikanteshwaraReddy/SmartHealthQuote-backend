"""
User document shape for MongoDB.

This TypedDict mirrors the exact structure stored in the `users` collection.
It is used only for type hints and serialisation helpers — never instantiated
to write to the DB (dicts are inserted directly).

Fields
------
_id         : MongoDB ObjectId (internal, never returned in API responses)
userId      : UUID4 string — the public-facing user identifier
fullName    : Display name
email       : Unique login email (lowercase)
passwordHash: bcrypt hash — NEVER included in any API response
role        : "user" | "admin"
accountStatus: "active" | "suspended" | "pending_verification"
emailVerified: Whether the email address has been confirmed
profile     : Mutable user profile sub-document
auth        : Auth meta-data sub-document (tokens, login tracking)
createdAt   : ISO datetime of account creation (UTC)
updatedAt   : ISO datetime of last document update (UTC)
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict, Literal


class UserProfile(TypedDict, total=False):
    phone: Optional[str]
    dateOfBirth: Optional[datetime]
    address: Optional[str]
    gender: Optional[str]


class UserAuth(TypedDict, total=False):
    # Refresh token (hashed with bcrypt) — None after logout
    refreshTokenHash: Optional[str]
    lastLogin: Optional[datetime]
    # Brute-force protection
    loginAttempts: int
    lockedUntil: Optional[datetime]
    # Future OAuth support
    oauthProviders: List[Dict[str, Any]]   # [{provider, providerId, linkedAt}]
    # Future OTP / password-reset
    otpSecret: Optional[str]
    passwordResetToken: Optional[str]
    passwordResetExpiry: Optional[datetime]


class UserDocument(TypedDict):
    userId: str
    fullName: str
    email: str
    passwordHash: str
    role: Literal["user", "admin"]
    accountStatus: Literal["active", "suspended", "pending_verification"]
    emailVerified: bool
    profile: UserProfile
    auth: UserAuth
    createdAt: datetime
    updatedAt: datetime


# Constant — fields that must NEVER appear in API responses
SENSITIVE_FIELDS: tuple[str, ...] = (
    "passwordHash",
    "auth",
    "_id",
)


def sanitise_user(doc: dict) -> dict:
    """Remove sensitive fields from a MongoDB user document before returning it."""
    return {k: v for k, v in doc.items() if k not in SENSITIVE_FIELDS}
