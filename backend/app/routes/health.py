from flask import Blueprint, jsonify
from .utils import get_rag

bp = Blueprint("health", __name__)

@bp.get("/health")
def health():
    return jsonify({"status": "ok"})

@bp.get("/rag/status")
def rag_status():
    """Report RAG index status and basic stats if available."""
    rag = get_rag()
    if rag is None:
        return jsonify({
            "status": "not_ready",
            "message": "RAG index not loaded. Ensure FAISS is installed and the index files exist (see INDEX_DIR)."
        })
    try:
        stats = rag.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500