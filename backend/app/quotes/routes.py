"""
Quotes and health-check routes.

POST /api/quote      — Generate a health insurance quote (auth optional)
GET  /health         — Server health check
GET  /rag/status     — FAISS index status
"""
from __future__ import annotations

import logging

from flask import Blueprint, jsonify
from pydantic import ValidationError

from ..middleware.auth_middleware import optional_jwt
from ..models.schemas import QuoteRequest
from ..services.quote_service import generate_quote, _get_rag
from ..utils.response import error_response

logger = logging.getLogger(__name__)
quote_bp = Blueprint("quote", __name__)
health_bp = Blueprint("health", __name__)


# ──────────────────────────────────────────────────────────────────────────────
# Health / Utility
# ──────────────────────────────────────────────────────────────────────────────

@health_bp.get("/health")
def health():
    """Simple liveness probe."""
    return jsonify({"status": "ok"})


@health_bp.get("/rag/status")
def rag_status():
    """Report whether the FAISS RAG index is loaded and return basic statistics."""
    rag = _get_rag()
    if rag is None:
        return jsonify({
            "status": "not_ready",
            "message": (
                "RAG index not loaded. Ensure FAISS is installed and the "
                "index files exist (see INDEX_DIR)."
            ),
        })
    try:
        stats = rag.get_stats()
        return jsonify(stats)
    except Exception as exc:
        logger.exception("Error fetching RAG stats.")
        return jsonify({"status": "error", "message": "Could not fetch index stats."}), 500


# ──────────────────────────────────────────────────────────────────────────────
# Quote
# ──────────────────────────────────────────────────────────────────────────────

@quote_bp.post("/quote")
@optional_jwt
def quote():
    """
    Generate a health insurance quote.

    Authentication is optional — unauthenticated requests still receive a quote.
    When a user IS authenticated (g.current_user is set), the quote can later
    be persisted to their history.

    POST /api/quote
    Body: QuoteRequest (all fields optional — see API.md)
    """
    from flask import request, g

    try:
        req_data = QuoteRequest.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return error_response("Invalid request data.", 400, "VALIDATION_ERROR")

    try:
        result = generate_quote(req_data)
    except Exception:
        logger.exception("Unexpected error generating quote.")
        return error_response("An internal error occurred while generating the quote.", 500)

    # Future: if g.current_user, save quote to DB here
    return jsonify(result.model_dump())
