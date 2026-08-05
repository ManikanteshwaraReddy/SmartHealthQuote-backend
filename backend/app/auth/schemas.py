"""
Pydantic request schemas for the auth endpoints.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    fullName: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., max_length=254)
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refreshToken: str


class UpdateProfileRequest(BaseModel):
    """Fields the user can update on their profile."""
    fullName: Optional[str] = Field(default=None, min_length=2, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=20)
    address: Optional[str] = Field(default=None, max_length=255)
    gender: Optional[str] = Field(default=None, max_length=20)


class ChangePasswordRequest(BaseModel):
    currentPassword: str = Field(..., min_length=1)
    newPassword: str = Field(..., min_length=8)
