"""
Authentication service — all business logic for auth operations.

This layer sits between the route handlers and the repository/security utils.
Routes: validate input shape → call service → return HTTP response.
Service: validate business rules → call repository → return dicts or raise exceptions.

Custom exceptions defined here let route handlers return the correct HTTP status
without containing any business logic themselves.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from flask import current_app

from ..models.user import sanitise_user
from ..repositories.user_repository import UserRepository
from ..utils.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
    verify_token_hash,
    decode_token,
)
from ..utils.validators import (
    validate_email_format,
    validate_full_name,
    validate_password_strength,
)

logger = logging.getLogger(__name__)

_repo = UserRepository()

# Maximum failed login attempts before account lockout
MAX_LOGIN_ATTEMPTS = 5
# Lockout duration in minutes
LOCKOUT_MINUTES = 15


# ──────────────────────────────────────────────────────────────────────────────
# Custom service exceptions
# ──────────────────────────────────────────────────────────────────────────────

class AuthError(Exception):
    """Base auth exception. Subclasses carry a status code."""
    def __init__(self, message: str, code: str = "AUTH_ERROR", status: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


class ValidationError(AuthError):
    def __init__(self, message: str, code: str = "VALIDATION_ERROR"):
        super().__init__(message, code=code, status=400)


class ConflictError(AuthError):
    def __init__(self, message: str, code: str = "CONFLICT"):
        super().__init__(message, code=code, status=409)


class UnauthorizedError(AuthError):
    def __init__(self, message: str, code: str = "UNAUTHORIZED"):
        super().__init__(message, code=code, status=401)


class AccountLockedError(AuthError):
    def __init__(self, message: str):
        super().__init__(message, code="ACCOUNT_LOCKED", status=423)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _build_token_pair(user_id: str, role: str) -> dict:
    """Create an access + refresh token pair and return them as a dict."""
    cfg = current_app.config
    access_token = create_access_token(
        user_id,
        role,
        cfg["JWT_SECRET"],
        cfg["ACCESS_TOKEN_EXPIRY_MINUTES"],
    )
    refresh_token = create_refresh_token(
        user_id,
        cfg["JWT_REFRESH_SECRET"],
        cfg["REFRESH_TOKEN_EXPIRY_DAYS"],
    )
    return {
        "accessToken": access_token,
        "refreshToken": refresh_token,
        "tokenType": "Bearer",
        "expiresIn": cfg["ACCESS_TOKEN_EXPIRY_MINUTES"] * 60,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Public service functions
# ──────────────────────────────────────────────────────────────────────────────

def register_user(full_name: str, email: str, password: str) -> dict:
    """
    Register a new user.

    Returns
    -------
    dict with keys: user (public user data), tokens (access + refresh)
    """
    # --- Validate inputs ---
    ok, err = validate_full_name(full_name)
    if not ok:
        raise ValidationError(err)

    ok, err = validate_email_format(email)
    if not ok:
        raise ValidationError(err)

    ok, err = validate_password_strength(password)
    if not ok:
        raise ValidationError(err)

    # --- Check uniqueness ---
    email = email.lower().strip()
    if _repo.email_exists(email):
        raise ConflictError(
            "An account with this email address already exists.",
            code="EMAIL_TAKEN",
        )

    # --- Build document ---
    now = datetime.now(tz=timezone.utc)
    user_id = str(uuid.uuid4())
    cfg = current_app.config

    user_doc = {
        "userId": user_id,
        "fullName": full_name.strip(),
        "email": email,
        "passwordHash": hash_password(password, rounds=cfg["BCRYPT_ROUNDS"]),
        "role": "user",
        "accountStatus": "active",
        "emailVerified": False,
        "profile": {
            "phone": None,
            "dateOfBirth": None,
            "address": None,
            "gender": None,
        },
        "auth": {
            "refreshTokenHash": None,
            "lastLogin": None,
            "loginAttempts": 0,
            "lockedUntil": None,
            "oauthProviders": [],
            "otpSecret": None,
            "passwordResetToken": None,
            "passwordResetExpiry": None,
        },
        "createdAt": now,
        "updatedAt": now,
    }

    _repo.create(user_doc)

    # --- Issue tokens ---
    tokens = _build_token_pair(user_id, "user")

    # Store hashed refresh token
    _repo.store_refresh_token_hash(
        user_id,
        hash_token(tokens["refreshToken"], rounds=cfg["BCRYPT_ROUNDS"]),
    )

    return {
        "user": sanitise_user(user_doc),
        "tokens": tokens,
    }


def login_user(email: str, password: str) -> dict:
    """
    Authenticate a user by email + password.

    Returns
    -------
    dict with keys: user (public user data), tokens (access + refresh)
    """
    if not email or not password:
        raise ValidationError("Email and password are required.")

    email = email.lower().strip()
    user = _repo.find_by_email(email)

    # --- Generic "invalid credentials" to prevent user enumeration ---
    if not user:
        raise UnauthorizedError("Invalid email or password.")

    # --- Account status checks ---
    if user.get("accountStatus") == "suspended":
        raise UnauthorizedError(
            "Your account has been suspended. Contact support.",
            code="ACCOUNT_SUSPENDED",
        )

    auth_meta = user.get("auth", {})

    # --- Brute-force lockout check ---
    locked_until = auth_meta.get("lockedUntil")
    if locked_until and datetime.now(tz=timezone.utc) < locked_until.replace(
        tzinfo=timezone.utc
    ):
        raise AccountLockedError(
            f"Account is temporarily locked due to too many failed login attempts. "
            f"Try again after {LOCKOUT_MINUTES} minutes."
        )

    # --- Password verification ---
    if not verify_password(password, user.get("passwordHash", "")):
        attempts = _repo.increment_login_attempts(user["userId"])
        if attempts >= MAX_LOGIN_ATTEMPTS:
            lock_until = datetime.now(tz=timezone.utc) + timedelta(
                minutes=LOCKOUT_MINUTES
            )
            _repo.lock_account(user["userId"], lock_until)
            raise AccountLockedError(
                f"Too many failed attempts. Account locked for {LOCKOUT_MINUTES} minutes."
            )
        raise UnauthorizedError("Invalid email or password.")

    # --- Success ---
    _repo.update_last_login(user["userId"])

    cfg = current_app.config
    tokens = _build_token_pair(user["userId"], user["role"])

    _repo.store_refresh_token_hash(
        user["userId"],
        hash_token(tokens["refreshToken"], rounds=cfg["BCRYPT_ROUNDS"]),
    )

    return {
        "user": sanitise_user(user),
        "tokens": tokens,
    }


def refresh_tokens(raw_refresh_token: str) -> dict:
    """
    Issue a new access token (and rotate the refresh token) given a valid refresh token.

    Token rotation: the old refresh token is invalidated and a fresh pair is issued.
    """
    cfg = current_app.config
    payload = decode_token(raw_refresh_token, cfg["JWT_REFRESH_SECRET"])

    if not payload or payload.get("type") != "refresh":
        raise UnauthorizedError(
            "Invalid or expired refresh token. Please log in again.",
            code="INVALID_REFRESH_TOKEN",
        )

    user_id = payload.get("sub")
    user = _repo.find_by_user_id(user_id)

    if not user:
        raise UnauthorizedError("User not found.", code="USER_NOT_FOUND")

    stored_hash = (user.get("auth") or {}).get("refreshTokenHash")
    if not stored_hash or not verify_token_hash(raw_refresh_token, stored_hash):
        # Token has been revoked (logout) or is reused — invalidate all sessions
        _repo.clear_refresh_token(user_id)
        raise UnauthorizedError(
            "Refresh token has been revoked. Please log in again.",
            code="TOKEN_REVOKED",
        )

    # Rotate: issue new pair
    tokens = _build_token_pair(user_id, user["role"])
    _repo.store_refresh_token_hash(
        user_id,
        hash_token(tokens["refreshToken"], rounds=cfg["BCRYPT_ROUNDS"]),
    )
    return tokens


def logout_user(user_id: str) -> None:
    """Revoke the stored refresh token for the given user (logout)."""
    _repo.clear_refresh_token(user_id)


def get_current_user(user_id: str) -> dict:
    """Return the sanitised public profile for the authenticated user."""
    user = _repo.find_by_user_id(user_id)
    if not user:
        raise UnauthorizedError("User not found.", code="USER_NOT_FOUND")
    return sanitise_user(user)


def update_user_profile(user_id: str, fields: dict) -> dict:
    """
    Update mutable profile fields for a user.

    Accepted top-level keys: fullName, phone, gender, address.
    Returns the updated sanitised user document.
    """
    user = _repo.find_by_user_id(user_id)
    if not user:
        raise UnauthorizedError("User not found.", code="USER_NOT_FOUND")

    # Separate top-level fields (fullName) from sub-document fields (profile.*)
    top_level = {}
    profile_fields = {}

    if "fullName" in fields:
        ok, err = validate_full_name(fields["fullName"])
        if not ok:
            raise ValidationError(err)
        top_level["fullName"] = fields["fullName"].strip()

    for key in ("phone", "gender", "address"):
        if key in fields:
            profile_fields[key] = fields[key]

    _repo.update_profile_fields(user_id, top_level, profile_fields)

    updated = _repo.find_by_user_id(user_id)
    return sanitise_user(updated)


def change_user_password(user_id: str, current_password: str, new_password: str) -> None:
    """
    Verify the current password then replace it with a new bcrypt hash.
    Also clears the stored refresh token to force re-login on all devices.
    """
    user = _repo.find_by_user_id(user_id)
    if not user:
        raise UnauthorizedError("User not found.", code="USER_NOT_FOUND")

    if not verify_password(current_password, user.get("passwordHash", "")):
        raise UnauthorizedError(
            "Current password is incorrect.",
            code="WRONG_CURRENT_PASSWORD",
        )

    ok, err = validate_password_strength(new_password)
    if not ok:
        raise ValidationError(err)

    cfg = current_app.config
    new_hash = hash_password(new_password, rounds=cfg["BCRYPT_ROUNDS"])
    _repo.update_password(user_id, new_hash)
    _repo.clear_refresh_token(user_id)  # revoke existing sessions
