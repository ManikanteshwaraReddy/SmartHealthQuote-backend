"""
Quote service — business logic extracted from the original route handler.

All functions in this module are pure from the perspective of the route:
they accept validated Pydantic models and return dicts / domain objects.
No Flask imports, no direct HTTP response construction.
"""
from __future__ import annotations

import logging
import os

from ..models.schemas import (
    QuoteRequest,
    QuoteAmountResponse,
    QuoteRecommendation,
    RetrievalResult,
    RetrievedContext,
)
from ..services.costing import CostMatrixCalculator

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Singleton accessors (lazy, thread-local-safe for gunicorn workers)
# These were previously global singletons in routes/utils.py.
# Moved here so they live in the correct service layer.
# ──────────────────────────────────────────────────────────────────────────────

_RAG = None
_EMB = None
_LLM = None


def _get_embedder():
    global _EMB
    if _EMB is None:
        from ..services.embedding import EmbeddingClient
        _EMB = EmbeddingClient()
    return _EMB


def _get_llm():
    global _LLM
    if _LLM is None:
        from ..services.llm import LLMClient
        _LLM = LLMClient()
    return _LLM


def _get_rag():
    """Return a RagIndex instance if available, else None (FAISS is optional)."""
    global _RAG
    if _RAG is not None:
        return _RAG

    idx_dir = os.getenv("INDEX_DIR", "backend/index")
    index_path = os.path.join(idx_dir, "faiss.index")
    meta_path = os.path.join(idx_dir, "meta.json")

    try:
        from ..services.rag import RagIndex
        rag = RagIndex()
        rag.load(index_path, meta_path)
        _RAG = rag
        return _RAG
    except FileNotFoundError:
        logger.warning("RAG index files not found — running without RAG.")
        return None
    except Exception as exc:
        logger.warning("Could not load RAG index (%s) — running without RAG.", exc)
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Public service functions
# ──────────────────────────────────────────────────────────────────────────────

def build_query_text(req: QuoteRequest) -> str:
    """Build a natural-language query string from the QuoteRequest fields."""
    parts = []
    if req.age is not None:               parts.append(f"Age: {req.age}")
    if req.gender:                        parts.append(f"Gender: {req.gender}")
    if req.location:                      parts.append(f"Location: {req.location}")
    if req.occupation:                    parts.append(f"Occupation: {req.occupation}")
    if req.number_of_insured_members:     parts.append(f"Members: {req.number_of_insured_members}")
    if req.pre_existing_conditions:       parts.append(f"Pre-existing: {req.pre_existing_conditions}")
    if req.past_medical_history:          parts.append(f"Past: {req.past_medical_history}")
    if req.family_medical_history:        parts.append(f"Family: {req.family_medical_history}")
    if req.bmi:                           parts.append(f"BMI: {req.bmi}")
    if req.pregnancy_status:              parts.append(f"Pregnancy: {req.pregnancy_status}")
    if req.smoking_tobacco_use:           parts.append(f"Smoking: {req.smoking_tobacco_use}")
    if req.alcohol_consumption:           parts.append(f"Alcohol: {req.alcohol_consumption}")
    if req.exercise_frequency:            parts.append(f"Exercise: {req.exercise_frequency}")
    if req.plan_type:                     parts.append(f"Plan Type: {req.plan_type}")
    if req.sum_insured:                   parts.append(f"Sum Insured: {req.sum_insured}")
    if req.policy_term_years:             parts.append(f"Term: {req.policy_term_years}")
    if req.premium_payment_mode:          parts.append(f"Payment: {req.premium_payment_mode}")
    if req.medicalHistory:                parts.append(f"Medical History: {req.medicalHistory}")
    if req.lifestyle:                     parts.append(f"Lifestyle: {req.lifestyle}")
    if req.coverageNeed:                  parts.append(f"Coverage Need: {req.coverageNeed}")
    return " ".join(parts) if parts else "Health insurance quote request"


def retrieve_similar_records(request_data: QuoteRequest) -> RetrievalResult:
    """Embed the profile and retrieve closest indexed insurance records via FAISS."""
    rag = _get_rag()
    if rag is None:
        return RetrievalResult(status="not_available")

    try:
        top_k = max(1, int(os.getenv("TOP_K", "8")))
        query_embedding = _get_embedder().embed_text(build_query_text(request_data))
        records = rag.search(query_embedding, top_k=top_k)
        matches = [
            RetrievedContext(
                id=record.get("row_id", record["id"]),
                score=record["score"],
                snippet=record.get("text", ""),
                premium_inr=record.get("premium_inr"),
            )
            for record in records
        ]
        return RetrievalResult(status="used", matches=matches)
    except Exception as exc:
        logger.warning("RAG retrieval failed: %s", exc)
        return RetrievalResult(status="failed")


def build_recommendation(
    request_data: QuoteRequest,
    matches: list[RetrievedContext],
    yearly_premium: float | None,
) -> QuoteRecommendation:
    """Use retrieved examples to generate a narrative recommendation via LLM."""
    generated = _get_llm().generate_quote(
        request_data,
        [match.model_dump() for match in matches],
    )
    coverage_details = generated.get("coverageDetails", [])
    if not isinstance(coverage_details, list):
        coverage_details = []

    return QuoteRecommendation(
        planName=str(generated.get("planName") or "Personalised health plan"),
        premiumINR=float(yearly_premium or 0),
        sumInsured=generated.get("sumInsured") or request_data.sum_insured,
        policyTermYears=generated.get("policyTermYears") or request_data.policy_term_years,
        paymentMode=generated.get("paymentMode") or request_data.premium_payment_mode,
        deductibleINR=generated.get("deductibleINR"),
        coinsurancePercent=generated.get("coinsurancePercent"),
        coverageDetails=[str(item) for item in coverage_details],
        rationale=str(generated.get("rationale") or "Recommendation based on similar profiles."),
        basedOnExamples=matches,
    )


def generate_quote(req: QuoteRequest) -> QuoteAmountResponse:
    """
    Orchestrate the full quote generation pipeline.

    1. Compute deterministic baseline via CostMatrixCalculator
    2. Optionally refine with LLM
    3. Optionally enrich with RAG recommendation
    """
    baseline = CostMatrixCalculator.compute_total_payable(req)
    breakdown = CostMatrixCalculator.compute_breakdown(req)

    use_llm = os.getenv("USE_LLM_FOR_AMOUNT", "true").lower() in ("1", "true", "yes")
    if use_llm:
        try:
            llm_result = _get_llm().generate_amount(req, baseline)
            amount = float(llm_result.get("totalPayableINR", baseline))
        except Exception as exc:
            logger.warning("LLM amount generation failed: %s — using baseline.", exc)
            amount = float(baseline)
    else:
        amount = float(baseline)

    retrieval = retrieve_similar_records(req)
    recommendation = None
    if retrieval.status == "used" and retrieval.matches:
        try:
            recommendation = build_recommendation(req, retrieval.matches, breakdown.get("Yearly"))
        except Exception as exc:
            # A failed recommendation must NOT turn a valid price quote into an error.
            logger.warning("Recommendation generation failed: %s", exc)

    return QuoteAmountResponse(
        totalPayableINR=amount,
        yearlyINR=breakdown.get("Yearly"),
        halfYearlyINR=breakdown.get("Half-Yearly"),
        quarterlyINR=breakdown.get("Quarterly"),
        monthlyINR=breakdown.get("Monthly"),
        recommendation=recommendation,
        retrieval=retrieval,
    )
