"""
JWT authentication middleware.

Decorators
----------
@jwt_required
    Requires a valid access token in the Authorization header.
    Sets flask.g.current_user to the decoded payload.
    Returns 401 if the token is missing, invalid, or expired.

@optional_jwt
    Attempts to decode the token if present.
    Sets flask.g.current_user to the payload or None.
    Never returns an error on its own — routes decide whether they need auth.

@role_required(role)
    Must be stacked AFTER @jwt_required.
    Returns 403 if the user's role does not match.

Usage
-----
    from app.middleware.auth_middleware import jwt_required, role_required

    @bp.get("/admin/users")
    @jwt_required
    @role_required("admin")
    def list_users():
        user = g.current_user  # {"sub": userId, "role": "admin", ...}
        ...
"""
from __future__ import annotations

import logging
from functools import wraps
from typing import Callable

from flask import current_app, g, request

from ..utils.response import error_response
from ..utils.security import decode_token

logger = logging.getLogger(__name__)


def _extract_bearer_token() -> str | None:
    """Extract the raw token string from the Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header[len("Bearer "):].strip()
    return token or None


def jwt_required(fn: Callable) -> Callable:
    """Decorator: require a valid access token."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _extract_bearer_token()
        if not token:
            return error_response(
                "Authentication required. Provide a Bearer token.",
                401,
                "MISSING_TOKEN",
            )

        payload = decode_token(token, current_app.config["JWT_SECRET"])

        if payload is None:
            return error_response(
                "Token is invalid or has expired. Please log in again.",
                401,
                "INVALID_TOKEN",
            )

        if payload.get("type") != "access":
            return error_response(
                "Invalid token type.",
                401,
                "WRONG_TOKEN_TYPE",
            )

        g.current_user = payload
        return fn(*args, **kwargs)

    return wrapper


def optional_jwt(fn: Callable) -> Callable:
    """
    Decorator: attach user payload to g if a valid token is present,
    otherwise set g.current_user = None and continue.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        g.current_user = None
        token = _extract_bearer_token()
        if token:
            payload = decode_token(token, current_app.config["JWT_SECRET"])
            if payload and payload.get("type") == "access":
                g.current_user = payload
        return fn(*args, **kwargs)

    return wrapper


def role_required(role: str) -> Callable:
    """
    Decorator factory: require that g.current_user has the given role.
    Must be placed AFTER @jwt_required.
    """

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = getattr(g, "current_user", None)
            if not user or user.get("role") != role:
                return error_response(
                    "You do not have permission to access this resource.",
                    403,
                    "INSUFFICIENT_ROLE",
                )
            return fn(*args, **kwargs)

        return wrapper

    return decorator
