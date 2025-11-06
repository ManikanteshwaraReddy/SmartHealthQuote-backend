import os
from ..models.schemas import QuoteRequest
from ..services.embedding import EmbeddingClient
from ..services.llm import LLMClient

# NOTE: We import RagIndex lazily inside get_rag to avoid hard dependency on faiss
# at app import time (useful on platforms where faiss is unavailable). This lets
# the API run and still generate default quotes without RAG.

_RAG = None
_EMB = None
_LLM = None

def get_embedder() -> EmbeddingClient:
    global _EMB
    if _EMB is None:
        _EMB = EmbeddingClient()
    return _EMB

def get_llm() -> LLMClient:
    global _LLM
    if _LLM is None:
        _LLM = LLMClient()
    return _LLM

def get_rag():
    """Return a RagIndex instance if available, else None.

    This function tolerates environments without FAISS or missing index files.
    """
    global _RAG
    if _RAG is not None:
        return _RAG

    idx_dir = os.getenv("INDEX_DIR", "backend/index")
    index_path = os.path.join(idx_dir, "faiss.index")
    meta_path = os.path.join(idx_dir, "meta.json")

    try:
        # Lazy import here so the app can run without faiss installed.
        from ..services.rag import RagIndex  # type: ignore
        rag = RagIndex()
        rag.load(index_path, meta_path)
        _RAG = rag
        return _RAG
    except FileNotFoundError:
        # Index not built yet; return None to allow non-RAG flow.
        _RAG = None
        return None
    except Exception:
        # Any other error (including ImportError for faiss) — proceed without RAG.
        _RAG = None
        return None

def build_query_text(req: QuoteRequest) -> str:
    parts = []
    if req.age is not None: parts.append(f"Age: {req.age}")
    if req.gender: parts.append(f"Gender: {req.gender}")
    if req.location: parts.append(f"Location: {req.location}")
    if req.occupation: parts.append(f"Occupation: {req.occupation}")
    if req.number_of_insured_members: parts.append(f"Members: {req.number_of_insured_members}")
    if req.pre_existing_conditions: parts.append(f"Pre-existing: {req.pre_existing_conditions}")
    if req.past_medical_history: parts.append(f"Past: {req.past_medical_history}")
    if req.family_medical_history: parts.append(f"Family: {req.family_medical_history}")
    if req.bmi: parts.append(f"BMI: {req.bmi}")
    if req.pregnancy_status: parts.append(f"Pregnancy: {req.pregnancy_status}")
    if req.smoking_tobacco_use: parts.append(f"Smoking: {req.smoking_tobacco_use}")
    if req.alcohol_consumption: parts.append(f"Alcohol: {req.alcohol_consumption}")
    if req.exercise_frequency: parts.append(f"Exercise: {req.exercise_frequency}")
    if req.plan_type: parts.append(f"Plan Type: {req.plan_type}")
    if req.sum_insured: parts.append(f"Sum Insured: {req.sum_insured}")
    if req.policy_term_years: parts.append(f"Term: {req.policy_term_years}")
    if req.premium_payment_mode: parts.append(f"Payment: {req.premium_payment_mode}")
    if req.medicalHistory: parts.append(f"Medical History: {req.medicalHistory}")
    if req.lifestyle: parts.append(f"Lifestyle: {req.lifestyle}")
    if req.coverageNeed: parts.append(f"Coverage Need: {req.coverageNeed}")
    
    return " ".join(parts) if parts else "Health insurance quote request"