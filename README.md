
# Backend - SmartHealthQuote

Flask backend that calculates health insurance total payable amount, with:
- Cost-matrix baseline (deterministic, fast)
- Optional LLM refinement for the final number (Ollama)
- Optional RAG ingestion (FAISS) for future retrieval use-cases

## Setup

### 1) Python environment
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Environment variables
Copy `.env.example` to `.env` and adjust if needed:
- OLLAMA_BASE_URL (default http://localhost:11434)
- GEN_MODEL (default mistral) — used only if USE_LLM_FOR_AMOUNT=true
- EMBEDDING_MODEL (e.g., all-minilm or nomic-embed-text) — only needed for RAG ingestion
- INDEX_DIR (default backend/index)
- USE_LLM_FOR_AMOUNT (true/false)

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
- When `USE_LLM_FOR_AMOUNT=true`, the final number is minimally adjusted by the LLM around the cost-matrix baseline; otherwise it’s purely cost-matrix.

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
docker run -p 8000:8000 -e OLLAMA_BASE_URL=http://host.docker.internal:11434 smarthealth-backend
```
Note: Ensure the container can reach your Ollama host if LLM use is enabled.
