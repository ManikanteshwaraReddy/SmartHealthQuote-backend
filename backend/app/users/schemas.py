"""
Public-facing user schemas (Pydantic models for API responses).

These are separate from the MongoDB TypedDict in models/user.py:
  - TypedDict  → internal document shape (matches Mongo)
  - Pydantic   → serialised API response shape (safe, validated, typed)

UserPublic omits all sensitive fields by design.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel


class UserProfileResponse(BaseModel):
    """Mutable user profile sub-object returned in API responses."""
    phone: Optional[str] = None
    dateOfBirth: Optional[datetime] = None
    address: Optional[str] = None
    gender: Optional[str] = None

    model_config = {"populate_by_name": True}


class UserPublic(BaseModel):
    """
    Safe user object returned in all API responses.

    Fields omitted:
      - passwordHash  (never exposed)
      - auth          (internal tokens and login tracking)
      - _id           (MongoDB internal)
    """
    userId: str
    fullName: str
    email: str
    role: Literal["user", "admin"]
    accountStatus: Literal["active", "suspended", "pending_verification"]
    emailVerified: bool
    profile: UserProfileResponse
    createdAt: datetime
    updatedAt: datetime

    model_config = {"populate_by_name": True}
