from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator

Gender = Literal["Male", "Female", "Other"]

class QuoteRequest(BaseModel):
    age: Optional[int] = None
    medicalHistory: Optional[str] = None
    lifestyle: Optional[str] = None
    coverageNeed: Optional[str] = None

    gender: Optional[Gender] = None
    location: Optional[str] = None
    occupation: Optional[str] = None
    number_of_insured_members: Optional[int] = Field(default=None, alias="numberOfInsuredMembers")
    family_details: Optional[str] = Field(default=None, alias="familyDetails")
    pre_existing_conditions: Optional[str] = Field(default=None, alias="preExistingConditions")
    past_medical_history: Optional[str] = Field(default=None, alias="pastMedicalHistory")
    family_medical_history: Optional[str] = Field(default=None, alias="familyMedicalHistory")
    height_cm: Optional[float] = Field(default=None, alias="heightCm")
    weight_kg: Optional[float] = Field(default=None, alias="weightKg")
    bmi: Optional[float] = None
    pregnancy_status: Optional[str] = Field(default=None, alias="pregnancyStatus")
    smoking_tobacco_use: Optional[str] = Field(default=None, alias="smokingTobaccoUse")
    alcohol_consumption: Optional[str] = Field(default=None, alias="alcoholConsumption")
    exercise_frequency: Optional[str] = Field(default=None, alias="exerciseFrequency")
    plan_type: Optional[str] = Field(default=None, alias="planType")
    sum_insured: Optional[int] = Field(default=None, alias="sumInsured")
    policy_term_years: Optional[int] = Field(default=None, alias="policyTermYears")
    premium_payment_mode: Optional[str] = Field(default=None, alias="premiumPaymentMode")

    @field_validator("age")
    @classmethod
    def check_age(cls, v):
        if v is not None and (v < 0 or v > 120):
            raise ValueError("age must be between 0 and 120")
        return v

class RetrievedContext(BaseModel):
    id: int
    score: float
    snippet: str
    premium_inr: Optional[float] = None

class QuoteResponse(BaseModel):
    planName: str
    premiumINR: float
    sumInsured: Optional[int] = None
    policyTermYears: Optional[int] = None
    paymentMode: Optional[str] = None
    deductibleINR: Optional[float] = None
    coinsurancePercent: Optional[float] = None
    coverageDetails: list[str]
    rationale: str
    basedOnExamples: list[RetrievedContext]

class QuoteAmountResponse(BaseModel):
    totalPayableINR: float
    yearlyINR: float | None = None
    halfYearlyINR: float | None = None
    quarterlyINR: float | None = None
    monthlyINR: float | None = None