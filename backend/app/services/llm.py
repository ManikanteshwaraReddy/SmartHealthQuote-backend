"""
LLM client with pluggable provider backends.

Supports two providers controlled by the ``LLM_PROVIDER`` environment variable:
  • **groq**   – Groq cloud API (default, for deployment / CI)
  • **ollama** – Local Ollama instance (for offline / local development)

The public interface (``generate_quote``, ``generate_amount``) is identical
regardless of provider, so the rest of the application never needs to change.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, List

from ..models.schemas import QuoteRequest

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Shared prompt builders (preserve ALL existing prompt engineering verbatim)
# ─────────────────────────────────────────────────────────────────────────────

def _build_profile_text(request: QuoteRequest) -> str:
    """Build a semicolon-separated user-profile string from the request."""
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

    return "; ".join(profile_parts) if profile_parts else "Basic health insurance request"


def _build_quote_prompt(request: QuoteRequest, context_examples: List[Dict[str, Any]]) -> str:
    """Build the full recommendation prompt."""
    context_text = ""
    if context_examples:
        context_text = "Similar insurance cases:\n"
        for i, example in enumerate(context_examples[:5], 1):
            context_text += f"{i}. {example['snippet']}"
            if example.get('premium_inr'):
                context_text += f" (Premium: ₹{example['premium_inr']})"
            context_text += "\n"

    profile_text = _build_profile_text(request)

    return f"""You are an expert health insurance advisor. Using the customer profile and the most similar prior cases, recommend a suitable health insurance plan.

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


def _build_amount_prompt(request: QuoteRequest, baseline_amount_inr: float | None = None) -> str:
    """Build the pricing-only prompt."""
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

    return f"""You are a pricing assistant. Based on the customer profile, output ONLY the total payable annual premium.

Customer Profile: {profile_text}
{baseline_text}

Rules:
- Output must be a single valid JSON object with exactly one key: totalPayableINR (a number).
- If a baseline is provided, adjust minimally around it considering risk factors.
- No text, no explanations, no other keys.

Example output:
{{"totalPayableINR": 18500.0}}
"""


def _default_quote_fallback(request: QuoteRequest, generated_text: str = "") -> Dict[str, Any]:
    """Return a safe default when JSON parsing fails."""
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


# ─────────────────────────────────────────────────────────────────────────────
# Groq backend
# ─────────────────────────────────────────────────────────────────────────────

class _GroqBackend:
    """LLM backend using the Groq cloud API."""

    def __init__(self):
        from groq import Groq

        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Set it in .env or as an environment variable, "
                "or switch to LLM_PROVIDER=ollama for local usage."
            )
        self.client = Groq(api_key=api_key)
        self.model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        logger.info("Groq LLM backend initialised (model=%s)", self.model)

    def _call(self, prompt: str, temperature: float = 0.3) -> str:
        """Send a chat completion request to Groq with retry logic."""
        from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
        from groq import RateLimitError, APIStatusError, APIConnectionError

        @retry(
            retry=retry_if_exception_type((RateLimitError, APIConnectionError)),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            reraise=True,
        )
        def _do_call():
            start = time.time()
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that responds only in valid JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=temperature,
                    response_format={"type": "json_object"},
                    max_tokens=1024,
                )
                elapsed = time.time() - start
                text = response.choices[0].message.content or ""
                logger.info(
                    "Groq request completed: model=%s, tokens=%s, latency=%.2fs",
                    self.model,
                    getattr(response.usage, "total_tokens", "N/A"),
                    elapsed,
                )
                return text
            except (RateLimitError, APIConnectionError):
                raise  # let tenacity retry
            except APIStatusError as exc:
                elapsed = time.time() - start
                logger.error(
                    "Groq API error: model=%s, status=%s, latency=%.2fs",
                    self.model,
                    exc.status_code,
                    elapsed,
                )
                raise RuntimeError(
                    f"Groq API returned status {exc.status_code}. "
                    "Check your GROQ_API_KEY and model name."
                ) from exc
            except Exception as exc:
                elapsed = time.time() - start
                logger.error(
                    "Groq request failed: model=%s, latency=%.2fs, error=%s",
                    self.model, elapsed, exc,
                )
                raise RuntimeError(f"Groq LLM request failed: {exc}") from exc

        return _do_call()

    def generate_quote(self, request: QuoteRequest, context_examples: List[Dict[str, Any]]) -> Dict[str, Any]:
        prompt = _build_quote_prompt(request, context_examples)
        generated_text = self._call(prompt, temperature=0.3)
        try:
            return json.loads(generated_text)
        except json.JSONDecodeError:
            logger.warning("Groq returned non-JSON for quote; using fallback.")
            return _default_quote_fallback(request, generated_text)

    def generate_amount(self, request: QuoteRequest, baseline_amount_inr: float | None = None) -> Dict[str, Any]:
        prompt = _build_amount_prompt(request, baseline_amount_inr)
        generated_text = self._call(prompt, temperature=0.2)
        try:
            return json.loads(generated_text)
        except json.JSONDecodeError:
            amount = baseline_amount_inr if baseline_amount_inr is not None else 15000.0
            return {"totalPayableINR": float(amount)}


# ─────────────────────────────────────────────────────────────────────────────
# Ollama backend (local fallback)
# ─────────────────────────────────────────────────────────────────────────────

class _OllamaBackend:
    """LLM backend using a local Ollama instance (original implementation)."""

    def __init__(self):
        import requests as _  # noqa: F401 — ensure requests is available

        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("GEN_MODEL", "mistral")
        logger.info("Ollama LLM backend initialised (url=%s, model=%s)", self.base_url, self.model)

    def generate_quote(self, request: QuoteRequest, context_examples: List[Dict[str, Any]]) -> Dict[str, Any]:
        import requests

        prompt = _build_quote_prompt(request, context_examples)

        start = time.time()
        try:
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
        except requests.exceptions.RequestException as exc:
            elapsed = time.time() - start
            logger.error("Ollama quote request failed: model=%s, latency=%.2fs, error=%s", self.model, elapsed, exc)
            raise RuntimeError(
                f"Ollama LLM request failed. Ensure Ollama is running at {self.base_url}. Error: {exc}"
            ) from exc

        elapsed = time.time() - start
        result = response.json()
        generated_text = result.get("response", "")
        logger.info("Ollama quote request completed: model=%s, latency=%.2fs", self.model, elapsed)

        try:
            return json.loads(generated_text)
        except json.JSONDecodeError:
            logger.warning("Ollama returned non-JSON for quote; using fallback.")
            return _default_quote_fallback(request, generated_text)

    def generate_amount(self, request: QuoteRequest, baseline_amount_inr: float | None = None) -> Dict[str, Any]:
        import requests

        prompt = _build_amount_prompt(request, baseline_amount_inr)

        start = time.time()
        try:
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
        except requests.exceptions.RequestException as exc:
            elapsed = time.time() - start
            logger.error("Ollama amount request failed: model=%s, latency=%.2fs, error=%s", self.model, elapsed, exc)
            raise RuntimeError(
                f"Ollama LLM request failed. Ensure Ollama is running at {self.base_url}. Error: {exc}"
            ) from exc

        elapsed = time.time() - start
        result = response.json()
        generated_text = result.get("response", "")
        logger.info("Ollama amount request completed: model=%s, latency=%.2fs", self.model, elapsed)

        try:
            return json.loads(generated_text)
        except json.JSONDecodeError:
            amount = baseline_amount_inr if baseline_amount_inr is not None else 15000.0
            return {"totalPayableINR": float(amount)}


# ─────────────────────────────────────────────────────────────────────────────
# Public factory — same class name so callers don't change
# ─────────────────────────────────────────────────────────────────────────────

class LLMClient:
    """Provider-agnostic LLM client.

    Delegates to either Groq (cloud) or Ollama (local) based on
    the ``LLM_PROVIDER`` environment variable.
    """

    def __init__(self):
        provider = os.getenv("LLM_PROVIDER", "groq").lower().strip()
        if provider == "ollama":
            self._backend = _OllamaBackend()
        elif provider == "groq":
            self._backend = _GroqBackend()
        else:
            raise ValueError(
                f"Unknown LLM_PROVIDER '{provider}'. Use 'groq' or 'ollama'."
            )
        logger.info("LLMClient ready (provider=%s)", provider)

    def generate_quote(self, request: QuoteRequest, context_examples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate insurance quote using LLM with RAG context."""
        return self._backend.generate_quote(request, context_examples)

    def generate_amount(self, request: QuoteRequest, baseline_amount_inr: float | None = None) -> Dict[str, Any]:
        """Ask the LLM to output ONLY the total payable amount as JSON.

        Returns: {"totalPayableINR": float}
        """
        return self._backend.generate_amount(request, baseline_amount_inr)