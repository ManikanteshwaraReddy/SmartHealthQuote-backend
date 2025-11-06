import os
import json
import requests
from typing import List, Dict, Any
from ..models.schemas import QuoteRequest

class LLMClient:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("GEN_MODEL", "mistral")
    
    def generate_quote(self, request: QuoteRequest, context_examples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate insurance quote using LLM with RAG context"""
        
        # Build context from similar examples
        context_text = ""
        if context_examples:
            context_text = "Similar insurance cases:\n"
            for i, example in enumerate(context_examples[:5], 1):
                context_text += f"{i}. {example['snippet']}"
                if example.get('premium_inr'):
                    context_text += f" (Premium: ₹{example['premium_inr']})"
                context_text += "\n"
        
        # Build user profile text
        profile_parts: List[str] = []
        if request.age is not None: profile_parts.append(f"Age: {request.age}")
        if request.gender: profile_parts.append(f"Gender: {request.gender}")
        if request.location: profile_parts.append(f"Location: {request.location}")
        if request.occupation: profile_parts.append(f"Occupation: {request.occupation}")
        if request.number_of_insured_members is not None: profile_parts.append(f"Family size: {request.number_of_insured_members}")
        if request.family_details: profile_parts.append(f"Family details: {request.family_details}")
        if request.pre_existing_conditions: profile_parts.append(f"Pre-existing conditions: {request.pre_existing_conditions}")
        if request.past_medical_history: profile_parts.append(f"Past medical history: {request.past_medical_history}")
        if request.family_medical_history: profile_parts.append(f"Family medical history: {request.family_medical_history}")

        # BMI: use provided or compute from height/weight if available
        bmi_val = request.bmi
        if bmi_val is None and request.height_cm and request.weight_kg and request.height_cm > 0:
            try:
                bmi_val = request.weight_kg / ((request.height_cm / 100.0) ** 2)
            except Exception:
                bmi_val = None
        if bmi_val is not None:
            profile_parts.append(f"BMI: {bmi_val:.1f}")

        if request.pregnancy_status: profile_parts.append(f"Pregnancy status: {request.pregnancy_status}")
        if request.smoking_tobacco_use: profile_parts.append(f"Smoking/tobacco: {request.smoking_tobacco_use}")
        if request.alcohol_consumption: profile_parts.append(f"Alcohol: {request.alcohol_consumption}")
        if request.exercise_frequency: profile_parts.append(f"Exercise: {request.exercise_frequency}")

        # Explicit needs and preferences
        if request.coverageNeed: profile_parts.append(f"Coverage need: {request.coverageNeed}")
        if request.medicalHistory: profile_parts.append(f"Medical history (free text): {request.medicalHistory}")
        if request.lifestyle: profile_parts.append(f"Lifestyle: {request.lifestyle}")

        # Insurance preferences
        if request.sum_insured is not None: profile_parts.append(f"Desired sum insured: ₹{request.sum_insured}")
        if request.policy_term_years is not None: profile_parts.append(f"Desired policy term: {request.policy_term_years} years")
        if request.premium_payment_mode: profile_parts.append(f"Preferred payment mode: {request.premium_payment_mode}")
        if request.plan_type: profile_parts.append(f"Plan type: {request.plan_type}")
        
        profile_text = "; ".join(profile_parts) if profile_parts else "Basic health insurance request"
        
        # Create the prompt
        prompt = f"""You are an expert health insurance advisor. Using the customer profile and the most similar prior cases, recommend a suitable health insurance plan.

{context_text}

Customer Profile: {profile_text}

Respond ONLY with a single valid JSON object (no code fences, no commentary) using this exact schema and key names:
{{
  "planName": "Specific plan name",
  "premiumINR": 15000.0,
  "sumInsured": 500000,
  "policyTermYears": 20,
  "paymentMode": "Yearly",
  "deductibleINR": 5000.0,
  "coinsurancePercent": 10.0,
  "coverageDetails": ["Coverage item 1", "Coverage item 2", "Coverage item 3"],
  "rationale": "Why this plan best fits the profile (refer to risk factors, lifestyle, family size, and similar cases)."
}}

Guidance:
- If the customer requested a sum insured, respect it unless unsafe; otherwise propose a reasonable value.
- Keep the premium realistic for the profile and justify it in the rationale.
- Consider pre-existing conditions, family history, BMI, pregnancy status, lifestyle and coverage needs.
- Use information from similar cases when helpful but do not copy verbatim.
- Output must be valid JSON only (no trailing commas, no additional keys).
"""

        # Call Ollama API
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.3}
            },
            timeout=60
        )
        response.raise_for_status()
        
        # Extract the generated text
        result = response.json()
        generated_text = result.get("response", "")
        
        try:
            # Try to parse as JSON
            return json.loads(generated_text)
        except json.JSONDecodeError:
            # If JSON parsing fails, return a default structure
            return {
                "planName": "Standard Health Plan",
                "premiumINR": 15000.0,
                "sumInsured": request.sum_insured or 500000,
                "policyTermYears": request.policy_term_years or 20,
                "paymentMode": request.premium_payment_mode or "Yearly",
                "deductibleINR": 5000.0,
                "coinsurancePercent": 10.0,
                "coverageDetails": [
                    "Hospitalization coverage",
                    "Pre and post hospitalization",
                    "Day care procedures",
                    "Ambulance charges"
                ],
                "rationale": f"Standard plan recommended based on provided information. LLM response: {generated_text[:200]}..."
            }

    def generate_amount(self, request: QuoteRequest, baseline_amount_inr: float | None = None) -> Dict[str, Any]:
        """Ask the LLM to output ONLY the total payable amount as JSON.

        Returns: {"totalPayableINR": float}
        """
        profile_parts = []
        if request.age is not None: profile_parts.append(f"Age: {request.age}")
        if request.gender: profile_parts.append(f"Gender: {request.gender}")
        if request.location: profile_parts.append(f"Location: {request.location}")
        if request.plan_type: profile_parts.append(f"Plan type: {request.plan_type}")
        if request.sum_insured is not None: profile_parts.append(f"Sum insured: ₹{request.sum_insured}")
        if request.number_of_insured_members is not None: profile_parts.append(f"Members: {request.number_of_insured_members}")
        if request.pre_existing_conditions: profile_parts.append(f"Pre-existing: {request.pre_existing_conditions}")
        if request.family_medical_history: profile_parts.append(f"Family history: {request.family_medical_history}")
        if request.smoking_tobacco_use: profile_parts.append(f"Smoking: {request.smoking_tobacco_use}")
        if request.alcohol_consumption: profile_parts.append(f"Alcohol: {request.alcohol_consumption}")
        if request.exercise_frequency: profile_parts.append(f"Exercise: {request.exercise_frequency}")
        if request.policy_term_years is not None: profile_parts.append(f"Policy term: {request.policy_term_years} years")
        profile_text = "; ".join(profile_parts) if profile_parts else "Basic request"

        baseline_text = f"Baseline (cost-matrix) estimate: ₹{baseline_amount_inr:.2f}." if baseline_amount_inr is not None else ""

        prompt = f"""You are a pricing assistant. Based on the customer profile, output ONLY the total payable annual premium.

Customer Profile: {profile_text}
{baseline_text}

Rules:
- Output must be a single valid JSON object with exactly one key: totalPayableINR (a number).
- If a baseline is provided, adjust minimally around it considering risk factors.
- No text, no explanations, no other keys.

Example output:
{{"totalPayableINR": 18500.0}}
"""

        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.2}
            },
            timeout=60
        )
        response.raise_for_status()
        result = response.json()
        generated_text = result.get("response", "")
        try:
            return json.loads(generated_text)
        except json.JSONDecodeError:
            # fallback to baseline or default
            amount = baseline_amount_inr if baseline_amount_inr is not None else 15000.0
            return {"totalPayableINR": float(amount)}