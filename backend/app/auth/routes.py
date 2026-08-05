"""
Auth routes — POST /auth/register|login|logout|refresh; GET /auth/me
             PATCH /auth/profile; POST /auth/change-password

Route handlers are intentionally thin:
  1. Parse + validate request body with Pydantic
  2. Call the service
  3. Catch AuthError subclasses and return the correct HTTP status
  4. Return success_response()

No business logic lives here.
"""
from __future__ import annotations

import logging

from flask import Blueprint, g, request
from pydantic import ValidationError as PydanticValidationError

from ..auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    UpdateProfileRequest,
)
from ..middleware.auth_middleware import jwt_required
from ..services.auth_service import (
    AuthError,
    change_user_password,
    get_current_user,
    login_user,
    logout_user,
    refresh_tokens,
    register_user,
    update_user_profile,
)
from ..utils.response import error_response, success_response

logger = logging.getLogger(__name__)
bp = Blueprint("auth", __name__)


# ──────────────────────────────────────────────────────────────────────────────
# POST /auth/register
# ──────────────────────────────────────────────────────────────────────────────

@bp.post("/register")
def register():
    """Register a new user account and return a token pair."""
    try:
        body = RegisterRequest.model_validate(request.get_json(silent=True) or {})
    except PydanticValidationError:
        return error_response("Invalid request data.", 400, code="VALIDATION_ERROR")

    try:
        result = register_user(body.fullName, body.email, body.password)
    except AuthError as exc:
        return error_response(exc.message, exc.status, exc.code)
    except Exception:
        logger.exception("Unexpected error during registration.")
        return error_response("An internal error occurred.", 500, "INTERNAL_ERROR")

    return success_response(result, 201)


# ──────────────────────────────────────────────────────────────────────────────
# POST /auth/login
# ──────────────────────────────────────────────────────────────────────────────

@bp.post("/login")
def login():
    """Authenticate with email + password and return a token pair."""
    try:
        body = LoginRequest.model_validate(request.get_json(silent=True) or {})
    except PydanticValidationError:
        return error_response("Email and password are required.", 400, "VALIDATION_ERROR")

    try:
        result = login_user(body.email, body.password)
    except AuthError as exc:
        return error_response(exc.message, exc.status, exc.code)
    except Exception:
        logger.exception("Unexpected error during login.")
        return error_response("An internal error occurred.", 500, "INTERNAL_ERROR")

    return success_response(result)


# ──────────────────────────────────────────────────────────────────────────────
# POST /auth/logout
# ──────────────────────────────────────────────────────────────────────────────

@bp.post("/logout")
@jwt_required
def logout():
    """Revoke the current refresh token (requires a valid access token)."""
    user_id = g.current_user["sub"]
    try:
        logout_user(user_id)
    except Exception:
        logger.exception("Unexpected error during logout.")
        return error_response("An internal error occurred.", 500, "INTERNAL_ERROR")

    return success_response({"message": "Logged out successfully."})


# ──────────────────────────────────────────────────────────────────────────────
# POST /auth/refresh
# ──────────────────────────────────────────────────────────────────────────────

@bp.post("/refresh")
def refresh():
    """Issue a new access token using a valid refresh token."""
    raw_token: str | None = None

    body_json = request.get_json(silent=True) or {}
    if body_json.get("refreshToken"):
        raw_token = body_json["refreshToken"]
    elif request.cookies.get("refreshToken"):
        raw_token = request.cookies.get("refreshToken")

    if not raw_token:
        return error_response("Refresh token is required.", 400, "MISSING_REFRESH_TOKEN")

    try:
        tokens = refresh_tokens(raw_token)
    except AuthError as exc:
        return error_response(exc.message, exc.status, exc.code)
    except Exception:
        logger.exception("Unexpected error during token refresh.")
        return error_response("An internal error occurred.", 500, "INTERNAL_ERROR")

    return success_response(tokens)


# ──────────────────────────────────────────────────────────────────────────────
# GET /auth/me
# ──────────────────────────────────────────────────────────────────────────────

@bp.get("/me")
@jwt_required
def me():
    """Return the authenticated user's public profile."""
    user_id = g.current_user["sub"]
    try:
        user = get_current_user(user_id)
    except AuthError as exc:
        return error_response(exc.message, exc.status, exc.code)
    except Exception:
        logger.exception("Unexpected error fetching /me.")
        return error_response("An internal error occurred.", 500, "INTERNAL_ERROR")

    return success_response({"user": user})


# ──────────────────────────────────────────────────────────────────────────────
# PATCH /auth/profile
# ──────────────────────────────────────────────────────────────────────────────

@bp.patch("/profile")
@jwt_required
def update_profile():
    """Update the authenticated user's profile fields (fullName, phone, gender, address)."""
    user_id = g.current_user["sub"]
    try:
        body = UpdateProfileRequest.model_validate(request.get_json(silent=True) or {})
    except PydanticValidationError:
        return error_response("Invalid profile data.", 400, "VALIDATION_ERROR")

    try:
        user = update_user_profile(user_id, body.model_dump(exclude_none=True))
    except AuthError as exc:
        return error_response(exc.message, exc.status, exc.code)
    except Exception:
        logger.exception("Unexpected error updating profile.")
        return error_response("An internal error occurred.", 500, "INTERNAL_ERROR")

    return success_response({"user": user})


# ──────────────────────────────────────────────────────────────────────────────
# POST /auth/change-password
# ──────────────────────────────────────────────────────────────────────────────

@bp.post("/change-password")
@jwt_required
def change_password():
    """Change the authenticated user's password."""
    user_id = g.current_user["sub"]
    try:
        body = ChangePasswordRequest.model_validate(request.get_json(silent=True) or {})
    except PydanticValidationError:
        return error_response("Current and new password are required.", 400, "VALIDATION_ERROR")

    try:
        change_user_password(user_id, body.currentPassword, body.newPassword)
    except AuthError as exc:
        return error_response(exc.message, exc.status, exc.code)
    except Exception:
        logger.exception("Unexpected error changing password.")
        return error_response("An internal error occurred.", 500, "INTERNAL_ERROR")

    return success_response({"message": "Password changed successfully."})
