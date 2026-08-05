
# Backend - SmartHealthQuote

Flask backend that calculates health insurance total payable amount, with:
- Cost-matrix baseline (deterministic, fast)
- Optional LLM refinement for the final number (Groq cloud or Ollama local)
- Optional RAG ingestion (FAISS) for retrieval-augmented recommendations

## Setup

### 1) Python environment
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Environment variables
Copy `.env.example` to `.env` and adjust if needed:

**LLM Provider** (`LLM_PROVIDER`):
| Value    | Description                        | Required vars                              |
|----------|------------------------------------|--------------------------------------------|
| `groq`   | Groq cloud API (default)           | `GROQ_API_KEY`, `GROQ_MODEL`               |
| `ollama` | Local Ollama instance              | `OLLAMA_BASE_URL`, `GEN_MODEL`             |

**Embedding Provider** (`EMBEDDING_PROVIDER`):
| Value    | Description                                    | Required vars        |
|----------|------------------------------------------------|----------------------|
| `local`  | sentence-transformers (default, no API key)     | `EMBEDDING_MODEL`    |
| `ollama` | Local Ollama embeddings                         | `OLLAMA_BASE_URL`, `EMBEDDING_MODEL` |

Other settings:
- `INDEX_DIR` (default `backend/index`)
- `USE_LLM_FOR_AMOUNT` (`true`/`false`) — whether to refine the cost-matrix amount with the LLM

### 3) Start the API
```powershell
python -m backend.app.main

# In another terminal
curl http://localhost:8000/health
```

### 4) (Optional) Ingest CSV for RAG
If you plan to use retrieval features later:
```powershell
python backend\scripts\ingest.py --csv backend\data\sample_insurance.csv --out backend\index
curl http://localhost:8000/rag/status
```

## Switching between Groq and Ollama

**For cloud deployment (e.g., Render):**
```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile
EMBEDDING_PROVIDER=local
```

**For local development with Ollama:**
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
GEN_MODEL=mistral
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=all-minilm
```

## API

### Health Check
```text
GET /health
```
Response: `{"status":"ok"}`

### Quote Amount Calculation
```text
POST /api/quote
Content-Type: application/json

{
  "age": 30,
  "gender": "Male",
  "location": "Mumbai",
  "numberOfInsuredMembers": 2,
  "preExistingConditions": "None",
  "smokingTobaccoUse": "No",
  "sumInsured": 500000,
  "planType": "Individual",
  "premiumPaymentMode": "Quarterly"  // Monthly | Quarterly | Half-Yearly | Yearly
}
```

Response:
```json
{
  "totalPayableINR": 15880.0,
  "yearlyINR": 63450.0,
  "halfYearlyINR": 32240.0,
  "quarterlyINR": 16410.0,
  "monthlyINR": 5460.0
}
```

Notes:
- `totalPayableINR` corresponds to the selected `premiumPaymentMode` (or Yearly if absent).
- Per-term fields are always included so you can display all options.
- When `USE_LLM_FOR_AMOUNT=true`, the final number is minimally adjusted by the LLM around the cost-matrix baseline; otherwise it's purely cost-matrix.

## CSV format (for optional RAG ingestion)
Common columns (script is tolerant to missing ones):
- Demographics: Age, Gender, Location, Occupation
- Family: Number_of_Insured_Members, Family_Details
- Health: Pre_existing_Conditions, Past_Medical_History, Family_Medical_History
- Physical: Height_cm, Weight_kg
- Lifestyle: Pregnancy_Status, Smoking_Tobacco_Use, Alcohol_Consumption, Exercise_Frequency
- Insurance: Plan_Type, Sum_Insured, Policy_Term_Years, Premium_Payment_Mode, Premium_INR

## Docker (optional)
```bash
docker build -t smarthealth-backend .
docker run -p 8000:8000 \
  -e LLM_PROVIDER=groq \
  -e GROQ_API_KEY=gsk_... \
  smarthealth-backend
```

For local Ollama via Docker:
```bash
docker run -p 8000:8000 \
  -e LLM_PROVIDER=ollama \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  smarthealth-backend
```
Note: Ensure the container can reach your Ollama host if using the Ollama provider.
