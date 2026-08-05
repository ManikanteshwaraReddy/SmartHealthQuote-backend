"""
Input validation helpers.

These functions return (is_valid: bool, error_message: str | None).
Keep them pure (no Flask or DB imports) so they are easily unit-testable.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple


# ──────────────────────────────────────────────────────────────────────────────
# Email
# ──────────────────────────────────────────────────────────────────────────────

_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def validate_email_format(email: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Check that *email* is a non-empty string in a valid format.

    Returns (True, None) on success or (False, error_message) on failure.
    """
    if not email or not isinstance(email, str):
        return False, "Email is required."
    email = email.strip()
    if len(email) > 254:
        return False, "Email address is too long."
    if not _EMAIL_RE.match(email):
        return False, "Email address format is invalid."
    return True, None


# ──────────────────────────────────────────────────────────────────────────────
# Password
# ──────────────────────────────────────────────────────────────────────────────

def validate_password_strength(password: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Enforce password policy:
      - At least 8 characters
      - At least 1 uppercase letter
      - At least 1 lowercase letter
      - At least 1 digit
      - At least 1 special character

    Returns (True, None) on success or (False, error_message) on failure.
    """
    if not password or not isinstance(password, str):
        return False, "Password is required."

    errors = []
    if len(password) < 8:
        errors.append("at least 8 characters")
    if not re.search(r"[A-Z]", password):
        errors.append("one uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("one lowercase letter")
    if not re.search(r"\d", password):
        errors.append("one digit")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-\[\]\\\/~`+=;\'"]', password):
        errors.append("one special character")

    if errors:
        return False, f"Password must contain: {', '.join(errors)}."
    return True, None


# ──────────────────────────────────────────────────────────────────────────────
# Full Name
# ──────────────────────────────────────────────────────────────────────────────

def validate_full_name(full_name: Optional[str]) -> Tuple[bool, Optional[str]]:
    """Check that the full name is a non-empty string of reasonable length."""
    if not full_name or not isinstance(full_name, str):
        return False, "Full name is required."
    name = full_name.strip()
    if len(name) < 2:
        return False, "Full name must be at least 2 characters."
    if len(name) > 100:
        return False, "Full name must not exceed 100 characters."
    return True, None
