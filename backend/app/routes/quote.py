import os
from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from ..models.schemas import QuoteRequest, QuoteAmountResponse
from ..services.costing import CostMatrixCalculator
from .utils import get_llm

bp = Blueprint("quote", __name__)

@bp.post("/quote")
def quote():
    try:
        # Parse request data
        try:
            req_data = QuoteRequest.model_validate(request.get_json() or {})
        except ValidationError as e:
            return jsonify({"error": "Invalid request data", "details": str(e)}), 400

        # Compute baseline using cost matrix (for selected payment mode)
        baseline = CostMatrixCalculator.compute_total_payable(req_data)
        # Compute breakdown for all modes
        breakdown = CostMatrixCalculator.compute_breakdown(req_data)

        # Optionally ask LLM to output only the amount (with minimal adjustment)
        use_llm = os.getenv("USE_LLM_FOR_AMOUNT", "true").lower() in ("1", "true", "yes")
        if use_llm:
            llm = get_llm()
            try:
                result = llm.generate_amount(req_data, baseline)
                amount = float(result.get("totalPayableINR", baseline))
            except Exception:
                amount = float(baseline)
        else:
            amount = float(baseline)

        # Map breakdown to response fields (the amount may be LLM-adjusted for selected mode only)
        response = QuoteAmountResponse(
            totalPayableINR=amount,
            yearlyINR=breakdown.get("Yearly"),
            halfYearlyINR=breakdown.get("Half-Yearly"),
            quarterlyINR=breakdown.get("Quarterly"),
            monthlyINR=breakdown.get("Monthly")
        )
        return jsonify(response.model_dump())

    except Exception as e:
        return jsonify({"error": "Internal server error", "details": str(e)}), 500