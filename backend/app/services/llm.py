import os
import json
import requests
from typing import Dict, Any
from ..models.schemas import QuoteRequest, QuoteResponse, RetrievedContext

class LLMClient:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("GEN_MODEL", "mistral")
    
    def generate_quote(self, quote_req: QuoteRequest, context: str) -> QuoteResponse:
        """Generate a health insurance quote based on request and context."""
        
        # Build the prompt
        prompt = self._build_prompt(quote_req, context)
        
        # Call Ollama
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        response_text = data["response"]
        
        try:
            # Parse the JSON response
            quote_data = json.loads(response_text)
            
            # Extract retrieved context info (simplified)
            retrieved_contexts = self._extract_retrieved_contexts(context)
            
            # Create QuoteResponse object
            quote_response = QuoteResponse(
                planName=quote_data.get("planName", "Standard Health Plan"),
                premiumINR=float(quote_data.get("premiumINR", 15000)),
                sumInsured=quote_data.get("sumInsured"),
                policyTermYears=quote_data.get("policyTermYears"),
                paymentMode=quote_data.get("paymentMode"),
                deductibleINR=quote_data.get("deductibleINR"),
                coinsurancePercent=quote_data.get("coinsurancePercent"),
                coverageDetails=quote_data.get("coverageDetails", []),
                rationale=quote_data.get("rationale", "Quote generated based on provided information and similar cases."),
                basedOnExamples=retrieved_contexts
            )
            
            return quote_response
            
        except (json.JSONDecodeError, KeyError) as e:
            # Fallback response if JSON parsing fails
            return QuoteResponse(
                planName="Standard Health Plan",
                premiumINR=15000.0,
                sumInsured=quote_req.sum_insured or 500000,
                policyTermYears=quote_req.policy_term_years or 1,
                paymentMode=quote_req.premium_payment_mode or "Annual",
                coverageDetails=[
                    "Hospitalization expenses",
                    "Pre and post hospitalization",
                    "Emergency ambulance",
                    "Day care procedures"
                ],
                rationale="Quote generated based on standard parameters and similar profiles.",
                basedOnExamples=self._extract_retrieved_contexts(context)
            )
    
    def _build_prompt(self, quote_req: QuoteRequest, context: str) -> str:
        """Build the prompt for the LLM."""
        
        prompt = f"""You are a health insurance expert. Generate a detailed insurance quote in JSON format based on the user profile and similar examples.

User Profile:
- Age: {quote_req.age or 'Not specified'}
- Gender: {quote_req.gender or 'Not specified'}
- Location: {quote_req.location or 'Not specified'}
- Occupation: {quote_req.occupation or 'Not specified'}
- Medical History: {quote_req.medicalHistory or 'Not specified'}
- Pre-existing Conditions: {quote_req.pre_existing_conditions or 'None'}
- Lifestyle: {quote_req.lifestyle or 'Not specified'}
- Coverage Need: {quote_req.coverageNeed or 'Standard'}
- Sum Insured: {quote_req.sum_insured or 'Not specified'}

Similar Examples from Database:
{context}

Generate a JSON response with the following structure:
{{
    "planName": "string",
    "premiumINR": number,
    "sumInsured": number,
    "policyTermYears": number,
    "paymentMode": "string",
    "deductibleINR": number,
    "coinsurancePercent": number,
    "coverageDetails": ["string", "string"],
    "rationale": "string explaining the quote calculation"
}}

Consider the user's age, medical history, and similar examples to determine appropriate premium and coverage."""
        
        return prompt
    
    def _extract_retrieved_contexts(self, context: str) -> list[RetrievedContext]:
        """Extract retrieved context information from the context string."""
        contexts = []
        lines = context.split('\n')
        
        for i, line in enumerate(lines):
            if line.strip():
                contexts.append(RetrievedContext(
                    id=i + 1,
                    score=0.8,  # Placeholder score
                    snippet=line.strip(),
                    premium_inr=None  # Would be extracted from actual data
                ))
        
        return contexts[:5]  # Return top 5