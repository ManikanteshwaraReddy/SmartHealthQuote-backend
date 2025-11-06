import math
from typing import Optional
from ..models.schemas import QuoteRequest

class CostMatrixCalculator:
    """
    Simple, transparent cost-matrix based premium estimator.
    Produces a baseline total payable amount in INR from input parameters.
    """

    # Base rates per sum insured band (annual) in INR
    BASE_BY_SUM_INSURED = [
        (300000, 7000),
        (500000, 9000),
        (700000, 12000),
        (1000000, 15000),
        (1500000, 19000),
        (2000000, 23000),
        (3000000, 30000),
        (5000000, 42000),
    ]

    # Multipliers
    AGE_BANDS = [
        (25, 0.90),
        (35, 1.00),
        (45, 1.20),
        (55, 1.45),
        (65, 1.80),
        (200, 2.20),
    ]
    BMI_BANDS = [
        (18.5, 0.95),
        (24.9, 1.00),
        (29.9, 1.15),
        (34.9, 1.30),
        (100, 1.50),
    ]
    LIFESTYLE_FACTORS = {
        "smoking": {"No": 1.00, "Occasional": 1.10, "Yes": 1.25},
        "alcohol": {"Never": 1.00, "Occasional": 1.05, "Regular": 1.10},
        "exercise": {
            "Sedentary": 1.10,
            "1-2 times/week": 1.05,
            "3-4 times/week": 1.00,
            "Daily": 0.97,
        },
    }
    PLAN_TYPE_FACTOR = {"Individual": 1.00, "Family": 1.20}
    MEMBERS_FACTOR_STEP = 0.08  # +8% per additional member beyond 1

    PREEXISTING_FACTOR = 1.10  # conservative uplift when present
    FAMILY_HISTORY_FACTOR = 1.05

    LOCATION_METRO = {"Mumbai", "Delhi", "Bengaluru", "Bangalore", "Chennai", "Kolkata", "Hyderabad", "Pune"}
    LOCATION_FACTOR_METRO = 1.08
    LOCATION_FACTOR_NON_METRO = 1.00

    PAYMENT_MODE_FACTOR = {
        "Monthly": 1.00,  # assume already annualized later
        "Quarterly": 0.99,
        "Half-Yearly": 0.985,
        "Yearly": 0.98,  # small discount for yearly
    }

    TERM_FACTOR = {
        1: 1.00,
        2: 0.99,
        3: 0.98,
    }

    @classmethod
    def _pick_base(cls, sum_insured: Optional[int]) -> float:
        if not sum_insured:
            return 15000.0
        for threshold, base in cls.BASE_BY_SUM_INSURED:
            if sum_insured <= threshold:
                return float(base)
        # above max band — extrapolate lightly
        return float(cls.BASE_BY_SUM_INSURED[-1][1]) * (sum_insured / cls.BASE_BY_SUM_INSURED[-1][0]) ** 0.3

    @classmethod
    def _band(cls, value: float, bands: list[tuple[float, float]]) -> float:
        for threshold, factor in bands:
            if value <= threshold:
                return factor
        return bands[-1][1]

    @classmethod
    def _bmi(cls, h_cm: Optional[float], w_kg: Optional[float], bmi: Optional[float]) -> Optional[float]:
        if bmi is not None:
            return bmi
        if h_cm and w_kg and h_cm > 0:
            try:
                return w_kg / ((h_cm / 100.0) ** 2)
            except Exception:
                return None
        return None

    @classmethod
    def _compute_base_annual(cls, req: QuoteRequest) -> float:
        """Compute annual premium BEFORE applying payment mode factor (but including term)."""
        base = cls._pick_base(req.sum_insured)

        # age
        age = req.age if req.age is not None else 35
        f_age = cls._band(float(age), cls.AGE_BANDS)

        # bmi
        bmi_val = cls._bmi(req.height_cm, req.weight_kg, req.bmi)
        f_bmi = cls._band(bmi_val, cls.BMI_BANDS) if bmi_val is not None else 1.0

        # lifestyle
        f_smoke = cls.LIFESTYLE_FACTORS["smoking"].get(req.smoking_tobacco_use or "No", 1.0)
        f_alcohol = cls.LIFESTYLE_FACTORS["alcohol"].get(req.alcohol_consumption or "Never", 1.0)
        f_ex = cls.LIFESTYLE_FACTORS["exercise"].get(req.exercise_frequency or "3-4 times/week", 1.0)

        # family size / plan type
        members = req.number_of_insured_members or 1
        beyond_one = max(0, members - 1)
        f_members = 1.0 + beyond_one * cls.MEMBERS_FACTOR_STEP
        f_plan = cls.PLAN_TYPE_FACTOR.get((req.plan_type or "Individual"), 1.0)

        # health history
        f_pre = cls.PREEXISTING_FACTOR if (req.pre_existing_conditions and req.pre_existing_conditions.strip()) else 1.0
        f_famh = cls.FAMILY_HISTORY_FACTOR if (req.family_medical_history and req.family_medical_history.strip()) else 1.0

        # location
        loc = (req.location or "").strip()
        f_loc = cls.LOCATION_FACTOR_METRO if (loc in cls.LOCATION_METRO) else cls.LOCATION_FACTOR_NON_METRO

        # term and payment
        term = req.policy_term_years or 1
        f_term = cls.TERM_FACTOR.get(term, 1.0)
        premium = base * f_age * f_bmi * f_smoke * f_alcohol * f_ex * f_members * f_plan * f_pre * f_famh * f_loc
        premium *= f_term

        # normalize and round to nearest 10
        premium = max(3000.0, premium)
        return round(premium / 10.0) * 10.0

    @classmethod
    def compute_total_payable(cls, req: QuoteRequest) -> float:
        """Compute total payable applying the preferred payment mode (single number)."""
        base_annual = cls._compute_base_annual(req)
        pay = req.premium_payment_mode or "Yearly"
        f_pay = cls.PAYMENT_MODE_FACTOR.get(pay, 1.0)
        total = max(3000.0, base_annual * f_pay)
        return round(total / 10.0) * 10.0

    @classmethod
    def compute_breakdown(cls, req: QuoteRequest) -> dict[str, float]:
        """Return per-installment amounts for common payment modes.

        Keys: Yearly, Half-Yearly, Quarterly, Monthly – values are payable per installment.
        """
        base_annual = cls._compute_base_annual(req)
        # Annual totals by mode (before splitting into installments)
        total_yearly = base_annual * cls.PAYMENT_MODE_FACTOR.get("Yearly", 1.0)
        total_half = base_annual * cls.PAYMENT_MODE_FACTOR.get("Half-Yearly", 1.0)
        total_quarter = base_annual * cls.PAYMENT_MODE_FACTOR.get("Quarterly", 1.0)
        total_month = base_annual * cls.PAYMENT_MODE_FACTOR.get("Monthly", 1.0)

        def _round2(x: float) -> float:
            x = max(3000.0 / 12.0, x)
            return round(x / 10.0) * 10.0

        breakdown = {
            "Yearly": round(max(3000.0, total_yearly) / 10.0) * 10.0,
            "Half-Yearly": _round2(total_half / 2.0),
            "Quarterly": _round2(total_quarter / 4.0),
            "Monthly": _round2(total_month / 12.0),
        }
        return breakdown
