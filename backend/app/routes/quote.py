import os
import logging
from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from ..models.schemas import QuoteRequest, QuoteResponse
from .utils import get_embedder, get_llm, get_rag, build_query_text

bp = Blueprint("quote", __name__)

@bp.post("/quote")
def quote():
    try:
        # Parse and validate request
        req_data = request.get_json()
        if not req_data:
            return jsonify({"error": "No JSON body provided"}), 400
            
        quote_req = QuoteRequest(**req_data)
        
        # Get services
        embedder = get_embedder()
        llm = get_llm()
        rag = get_rag()
        
        # Build query text
        query_text = build_query_text(quote_req)
        
        # Get embeddings and search
        query_embedding = embedder.embed_text(query_text)
        top_k = int(os.getenv("TOP_K", "8"))
        results = rag.search(query_embedding, top_k=top_k)
        
        # Build context for LLM
        context_parts = []
        for result in results:
            context_parts.append(f"Example {result['id']}: {result['snippet']} (Premium: ₹{result.get('premium_inr', 'N/A')})")
        
        context = "\n".join(context_parts)
        
        # Generate quote using LLM
        response = llm.generate_quote(quote_req, context)
        
        return jsonify(response.model_dump())
        
    except ValidationError as e:
        return jsonify({"error": "Invalid request data", "details": e.errors()}), 400
    except FileNotFoundError:
        return jsonify({"error": "FAISS index not found. Please run ingestion first."}), 500
    except Exception as e:
        logging.error(f"Error generating quote: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500