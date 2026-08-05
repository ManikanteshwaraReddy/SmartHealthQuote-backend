"""
Standardised API response helpers.

Every route handler must return via these functions so that the API shape
is consistent regardless of success or failure.

Success shape
-------------
{
  "success": true,
  "data": { ... }
}

Error shape
-----------
{
  "success": false,
  "error": {
    "message": "Human-readable error",
    "code": "MACHINE_READABLE_CODE"   (optional)
  }
}
"""
from __future__ import annotations

from typing import Any, Optional

from flask import jsonify


def success_response(data: Any, status: int = 200):
    """Return a Flask JSON response for a successful operation."""
    return jsonify({"success": True, "data": data}), status


def error_response(
    message: str,
    status: int,
    code: Optional[str] = None,
):
    """
    Return a Flask JSON response for an error.

    Parameters
    ----------
    message : str
        Human-readable description shown to API consumers.
    status  : int
        HTTP status code.
    code    : str, optional
        Machine-readable error code (e.g. "EMAIL_TAKEN", "INVALID_TOKEN").
    """
    body: dict = {"success": False, "error": {"message": message}}
    if code:
        body["error"]["code"] = code  # type: ignore[index]
    return jsonify(body), status
