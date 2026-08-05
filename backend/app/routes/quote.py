import os
from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from ..models.schemas import (
    QuoteRequest,
    QuoteAmountResponse,
    QuoteRecommendation,
    RetrievalResult,
    RetrievedContext,
)
from ..services.costing import CostMatrixCalculator
from .utils import build_query_text, get_embedder, get_llm, get_rag

bp = Blueprint("quote", __name__)


def retrieve_similar_records(request_data: QuoteRequest) -> RetrievalResult:
    """Embed the profile and retrieve the closest indexed insurance records."""
    rag = get_rag()
    if rag is None:
        return RetrievalResult(status="not_available")

    try:
        query_embedding = get_embedder().embed_text(build_query_text(request_data))
        top_k = max(1, int(os.getenv("TOP_K", "8")))
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
    except Exception:
        # Retrieval is an optional enhancement; quote pricing remains available.
        return RetrievalResult(status="failed")


def build_recommendation(
    request_data: QuoteRequest,
    matches: list[RetrievedContext],
    yearly_premium: float | None,
) -> QuoteRecommendation:
    """Use retrieved examples to generate a narrative recommendation.

    Premium values continue to come from the deterministic calculator so the
    explanation cannot contradict the price returned by this endpoint.
    """
    generated = get_llm().generate_quote(
        request_data,
        [match.model_dump() for match in matches],
    )
    coverage_details = generated.get("coverageDetails", [])
    if not isinstance(coverage_details, list):
        coverage_details = []

    return QuoteRecommendation(
        planName=str(generated.get("planName") or "Personalized health plan"),
        premiumINR=float(yearly_premium or 0),
        sumInsured=generated.get("sumInsured") or request_data.sum_insured,
        policyTermYears=generated.get("policyTermYears") or request_data.policy_term_years,
        paymentMode=generated.get("paymentMode") or request_data.premium_payment_mode,
        deductibleINR=generated.get("deductibleINR"),
        coinsurancePercent=generated.get("coinsurancePercent"),
        coverageDetails=[str(item) for item in coverage_details],
        rationale=str(generated.get("rationale") or "Recommendation based on similar insurance profiles."),
        basedOnExamples=matches,
    )


@bp.post("/quote")
def quote():
    try:
        try:
            req_data = QuoteRequest.model_validate(request.get_json() or {})
        except ValidationError as e:
            return jsonify({"error": "Invalid request data", "details": str(e)}), 400

        baseline = CostMatrixCalculator.compute_total_payable(req_data)
        breakdown = CostMatrixCalculator.compute_breakdown(req_data)

        use_llm_for_amount = os.getenv("USE_LLM_FOR_AMOUNT", "true").lower() in ("1", "true", "yes")
        if use_llm_for_amount:
            try:
                amount = float(get_llm().generate_amount(req_data, baseline).get("totalPayableINR", baseline))
            except Exception:
                amount = float(baseline)
        else:
            amount = float(baseline)

        retrieval = retrieve_similar_records(req_data)
        recommendation = None
        if retrieval.status == "used" and retrieval.matches:
            try:
                recommendation = build_recommendation(req_data, retrieval.matches, breakdown.get("Yearly"))
            except Exception:
                # A failed recommendation must not turn a valid price quote into an error.
                pass

        response = QuoteAmountResponse(
            totalPayableINR=amount,
            yearlyINR=breakdown.get("Yearly"),
            halfYearlyINR=breakdown.get("Half-Yearly"),
            quarterlyINR=breakdown.get("Quarterly"),
            monthlyINR=breakdown.get("Monthly"),
            recommendation=recommendation,
            retrieval=retrieval,
        )
        return jsonify(response.model_dump())
    except Exception as e:
        return jsonify({"error": "Internal server error", "details": str(e)}), 500