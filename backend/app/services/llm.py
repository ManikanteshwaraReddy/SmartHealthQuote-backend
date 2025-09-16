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
        profile_parts = []
        if request.age: profile_parts.append(f"Age: {request.age}")
        if request.gender: profile_parts.append(f"Gender: {request.gender}")
        if request.location: profile_parts.append(f"Location: {request.location}")
        if request.occupation: profile_parts.append(f"Occupation: {request.occupation}")
        if request.number_of_insured_members: profile_parts.append(f"Family size: {request.number_of_insured_members}")
        if request.pre_existing_conditions: profile_parts.append(f"Pre-existing conditions: {request.pre_existing_conditions}")
        if request.past_medical_history: profile_parts.append(f"Past medical history: {request.past_medical_history}")
        if request.smoking_tobacco_use: profile_parts.append(f"Smoking/tobacco: {request.smoking_tobacco_use}")
        if request.alcohol_consumption: profile_parts.append(f"Alcohol: {request.alcohol_consumption}")
        if request.exercise_frequency: profile_parts.append(f"Exercise: {request.exercise_frequency}")
        if request.sum_insured: profile_parts.append(f"Desired sum insured: ₹{request.sum_insured}")
        if request.plan_type: profile_parts.append(f"Plan type: {request.plan_type}")
        
        profile_text = "; ".join(profile_parts) if profile_parts else "Basic health insurance request"
        
        # Create the prompt
        prompt = f"""You are an expert insurance advisor. Based on the customer profile and similar cases, provide a health insurance quote in JSON format.

{context_text}

Customer Profile: {profile_text}

Generate a comprehensive insurance quote with the following JSON structure:
{{
  "planName": "Specific plan name",
  "premiumINR": 15000.0,
  "sumInsured": 500000,
  "policyTermYears": 20,
  "paymentMode": "Yearly",
  "deductibleINR": 5000.0,
  "coinsurancePercent": 10.0,
  "coverageDetails": ["Coverage item 1", "Coverage item 2", "Coverage item 3"],
  "rationale": "Detailed explanation of why this quote is appropriate for the customer"
}}

Consider the customer's age, health conditions, lifestyle, and requirements. The premium should be reasonable and justified. Provide only valid JSON response."""

        # Call Ollama API
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "format": "json"
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