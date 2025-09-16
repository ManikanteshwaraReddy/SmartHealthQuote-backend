import os
import json
from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from ..models.schemas import QuoteRequest, QuoteResponse, RetrievedContext
from .utils import get_embedder, get_llm, get_rag, build_query_text

bp = Blueprint("quote", __name__)

@bp.post("/quote")
def quote():
    try:
        # Parse request data
        try:
            req_data = QuoteRequest.model_validate(request.get_json() or {})
        except ValidationError as e:
            return jsonify({"error": "Invalid request data", "details": str(e)}), 400
        
        # Build query string
        query_text = build_query_text(req_data)
        
        # Get services
        try:
            embedder = get_embedder()
            rag = get_rag()
            llm = get_llm()
        except Exception as e:
            return jsonify({"error": "Service initialization failed", "details": str(e)}), 500
        
        # Get embedding for query
        try:
            query_embedding = embedder.embed_text(query_text)
        except Exception as e:
            return jsonify({"error": "Embedding generation failed", "details": str(e)}), 500
        
        # Search similar examples
        try:
            top_k = int(os.getenv("TOP_K", "8"))
            similar_results = rag.search(query_embedding, top_k=top_k)
        except Exception as e:
            return jsonify({"error": "RAG search failed", "details": str(e)}), 500
        
        # Prepare context for LLM
        context_examples = []
        for result in similar_results:
            context_examples.append({
                "id": result["id"],
                "score": result["score"],
                "snippet": result["text"],
                "premium_inr": result.get("premium_inr")
            })
        
        # Generate LLM response
        try:
            llm_response = llm.generate_quote(req_data, context_examples)
            
            # Parse LLM JSON response
            if isinstance(llm_response, str):
                llm_data = json.loads(llm_response)
            else:
                llm_data = llm_response
            
            # Convert context examples to RetrievedContext objects
            retrieved_contexts = [
                RetrievedContext(
                    id=ctx["id"],
                    score=ctx["score"], 
                    snippet=ctx["snippet"],
                    premium_inr=ctx.get("premium_inr")
                ) for ctx in context_examples
            ]
            
            # Create response object
            response = QuoteResponse(
                planName=llm_data.get("planName", "Standard Health Plan"),
                premiumINR=float(llm_data.get("premiumINR", 15000)),
                sumInsured=llm_data.get("sumInsured"),
                policyTermYears=llm_data.get("policyTermYears"),
                paymentMode=llm_data.get("paymentMode"),
                deductibleINR=llm_data.get("deductibleINR"),
                coinsurancePercent=llm_data.get("coinsurancePercent"),
                coverageDetails=llm_data.get("coverageDetails", []),
                rationale=llm_data.get("rationale", "Based on provided information and similar cases."),
                basedOnExamples=retrieved_contexts
            )
            
            return jsonify(response.model_dump())
            
        except Exception as e:
            return jsonify({"error": "LLM generation failed", "details": str(e)}), 500
            
    except Exception as e:
        return jsonify({"error": "Internal server error", "details": str(e)}), 500