"""
User repository — all MongoDB operations for the users collection.

Rules
-----
* No business logic here; only database reads/writes.
* All methods accept and return plain Python dicts (MongoDB documents).
* The service layer is responsible for transforming dicts into response objects.
* Exceptions propagate upward to the service layer, which decides how to handle them.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from pymongo.errors import DuplicateKeyError

from ..database.connection import get_db

logger = logging.getLogger(__name__)


class UserRepository:

    @property
    def _collection(self):
        return get_db()["users"]

    # ──────────────────────────────────────────────────────────────────────────
    # Read
    # ──────────────────────────────────────────────────────────────────────────

    def find_by_email(self, email: str) -> Optional[dict]:
        """Return the full user document by email (lowercase), or None."""
        return self._collection.find_one({"email": email.lower().strip()})

    def find_by_user_id(self, user_id: str) -> Optional[dict]:
        """Return the full user document by public userId, or None."""
        return self._collection.find_one({"userId": user_id})

    def email_exists(self, email: str) -> bool:
        """Return True if the email is already registered."""
        return (
            self._collection.count_documents(
                {"email": email.lower().strip()}, limit=1
            )
            > 0
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Write
    # ──────────────────────────────────────────────────────────────────────────

    def create(self, user_doc: dict) -> str:
        """
        Insert a new user document.

        Returns the string userId on success.
        Raises DuplicateKeyError if the email already exists.
        """
        result = self._collection.insert_one(user_doc)
        logger.info("New user created: %s", user_doc.get("userId"))
        return user_doc["userId"]

    def update_last_login(self, user_id: str) -> None:
        """Stamp lastLogin and reset loginAttempts on successful login."""
        self._collection.update_one(
            {"userId": user_id},
            {
                "$set": {
                    "auth.lastLogin": datetime.now(tz=timezone.utc),
                    "auth.loginAttempts": 0,
                    "auth.lockedUntil": None,
                    "updatedAt": datetime.now(tz=timezone.utc),
                }
            },
        )

    def store_refresh_token_hash(self, user_id: str, token_hash: str) -> None:
        """Save a bcrypt hash of the refresh token to enable logout revocation."""
        self._collection.update_one(
            {"userId": user_id},
            {
                "$set": {
                    "auth.refreshTokenHash": token_hash,
                    "updatedAt": datetime.now(tz=timezone.utc),
                }
            },
        )

    def clear_refresh_token(self, user_id: str) -> None:
        """Remove the stored refresh token hash (logout / token rotation)."""
        self._collection.update_one(
            {"userId": user_id},
            {
                "$set": {
                    "auth.refreshTokenHash": None,
                    "updatedAt": datetime.now(tz=timezone.utc),
                }
            },
        )

    def increment_login_attempts(self, user_id: str) -> int:
        """
        Increment failed login attempts counter.

        Returns the new attempt count so the service layer can decide whether
        to lock the account.
        """
        result = self._collection.find_one_and_update(
            {"userId": user_id},
            {
                "$inc": {"auth.loginAttempts": 1},
                "$set": {"updatedAt": datetime.now(tz=timezone.utc)},
            },
            return_document=True,
        )
        return result["auth"]["loginAttempts"] if result else 0

    def lock_account(self, user_id: str, until: datetime) -> None:
        """Lock the account until the given datetime (brute-force protection)."""
        self._collection.update_one(
            {"userId": user_id},
            {
                "$set": {
                    "auth.lockedUntil": until,
                    "updatedAt": datetime.now(tz=timezone.utc),
                }
            },
        )

    def update_profile_fields(
        self,
        user_id: str,
        top_level: dict,
        profile_fields: dict,
    ) -> None:
        """
        Update top-level fields (e.g. fullName) and profile sub-document fields together.

        top_level   : dict of root-level document fields to set (e.g. {"fullName": "..."})
        profile_fields : dict of profile sub-doc fields (e.g. {"phone": "..."})
        """
        set_fields: dict = {}

        for k, v in top_level.items():
            set_fields[k] = v

        for k, v in profile_fields.items():
            set_fields[f"profile.{k}"] = v

        set_fields["updatedAt"] = datetime.now(tz=timezone.utc)
        self._collection.update_one({"userId": user_id}, {"$set": set_fields})

    def update_password(self, user_id: str, new_hash: str) -> None:
        """Replace the stored password hash."""
        self._collection.update_one(
            {"userId": user_id},
            {
                "$set": {
                    "passwordHash": new_hash,
                    "updatedAt": datetime.now(tz=timezone.utc),
                }
            },
        )
