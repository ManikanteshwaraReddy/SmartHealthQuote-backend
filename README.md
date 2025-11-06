<<<<<<< HEAD
# SmartHealthQuote
## Backend:
=======
# Backend - SmartHealthQuote
>>>>>>> 63441b0 (cost matrix included)

Flask backend providing health insurance quote API using RAG (Retrieval-Augmented Generation) with Ollama and FAISS.

## Architecture

- **Flask API** with CORS support
- **Pydantic** for request/response validation
- **Ollama** for LLM generation (mistral) and embeddings (all-minilm → all-MiniLM-L6-v2)
- **FAISS** for vector similarity search with L2-normalized embeddings
- **RAG pipeline**: CSV ingestion → FAISS index → contextual quote generation

## Setup

### 1. Prerequisites

Install and start Ollama:
```bash
# Install Ollama (see https://ollama.ai)
# Then pull required models:
ollama pull mistral
ollama pull all-minilm
```

### 2. Python Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env if needed (defaults should work for local development)
```

### 4. Data Ingestion

<<<<<<< HEAD
```bash
# Ingest CSV data to build FAISS index
python backend/scripts/ingest.py --csv backend/data/health_insurance_1part_4.csv --out backend/index
=======
Windows PowerShell example:

```powershell
# Ingest CSV data to build FAISS index
python backend\scripts\ingest.py --csv backend\data\sample_insurance.csv --out backend\index

# Verify RAG index status (run server first as shown below)
curl http://localhost:8000/rag/status
>>>>>>> 63441b0 (cost matrix included)
```

This creates:
- `backend/index/faiss.index` - FAISS vector index
- `backend/index/meta.json` - Document metadata

<<<<<<< HEAD
### 5. Start the API Server

```bash
# Development mode
python -m backend.app.main

# Production mode with gunicorn
=======
CSV template: `backend/data/sample_insurance.csv`

If your CSV has different columns, you can adjust `backend/scripts/ingest.py` in `build_text_representation` to include the fields you care about. The script is tolerant of missing columns.

### 5. Start the API Server

```powershell
# Development mode
python -m backend.app.main

# Then, check health and RAG status in another PowerShell window:
curl http://localhost:8000/health
curl http://localhost:8000/rag/status

# Production mode with gunicorn (optional)
>>>>>>> 63441b0 (cost matrix included)
gunicorn -c gunicorn.conf.py backend.app.main:app
```

## API Endpoints

### Health Check
```bash
GET /health
```
Returns: `{"status": "ok"}`

<<<<<<< HEAD
### Quote Generation
=======
### Quote Amount Calculation
>>>>>>> 63441b0 (cost matrix included)
```bash
POST /api/quote
Content-Type: application/json

{
  "age": 30,
  "gender": "Male",
  "location": "Mumbai",
<<<<<<< HEAD
  "occupation": "Software Engineer",
=======
>>>>>>> 63441b0 (cost matrix included)
  "numberOfInsuredMembers": 2,
  "preExistingConditions": "None",
  "smokingTobaccoUse": "No",
  "sumInsured": 500000,
  "planType": "Individual"
}
```

<<<<<<< HEAD
Returns structured quote with:
- Plan details (name, premium, sum insured, etc.)
- Coverage details
- Rationale based on similar cases
- Retrieved context examples
=======
Returns:
```json
{ "totalPayableINR": 14230.0 }
```
>>>>>>> 63441b0 (cost matrix included)

## Models

### Ollama Models
<<<<<<< HEAD
- **Generation**: `mistral` (configurable via `GEN_MODEL`)
- **Embeddings**: `all-minilm` → maps to `all-MiniLM-L6-v2` sentence transformer (configurable via `EMBEDDING_MODEL`)
=======
- **Generation**: `mistral` (configurable via `GEN_MODEL`) — used optionally to refine amount and ensure consistent formatting
- **Embeddings**: `all-minilm` or `nomic-embed-text` (configurable via `EMBEDDING_MODEL`) — used only for RAG ingestion; not required for amount-only responses
>>>>>>> 63441b0 (cost matrix included)

### FAISS Index
- **Similarity**: Inner product on L2-normalized vectors (equivalent to cosine similarity)
- **Dimension**: 384 (all-MiniLM-L6-v2 embedding size)

## Configuration

Environment variables (see `.env.example`):

- `OLLAMA_BASE_URL`: Ollama server URL (default: http://localhost:11434)
- `GEN_MODEL`: LLM model for generation (default: mistral)
- `EMBEDDING_MODEL`: Model for embeddings (default: all-minilm)
- `INDEX_DIR`: Directory for FAISS index files (default: backend/index)
- `CORS_ORIGINS`: Allowed CORS origins (comma-separated)
- `TOP_K`: Number of similar examples to retrieve (default: 8)
<<<<<<< HEAD
=======
- `USE_LLM_FOR_AMOUNT`: When true, uses LLM to output only `{ "totalPayableINR": number }` around the cost-matrix baseline. When false, returns baseline directly.
>>>>>>> 63441b0 (cost matrix included)

## Development

### Adding New Data Sources

1. Place CSV files in `backend/data/`
2. Run ingestion script: `python backend/scripts/ingest.py --csv path/to/file.csv --out backend/index`
3. Restart the API server

### CSV Format

Expected columns (flexible, script handles missing values):
- Demographics: Age, Gender, Location, Occupation
- Family: Number_of_Insured_Members, Family_Details
- Health: Pre_existing_Conditions, Past_Medical_History, Family_Medical_History
- Physical: Height_cm, Weight_kg
- Lifestyle: Pregnancy_Status, Smoking_Tobacco_Use, Alcohol_Consumption, Exercise_Frequency
- Insurance: Plan_Type, Sum_Insured, Policy_Term_Years, Premium_Payment_Mode, Premium_INR

### Testing

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test quote endpoint
curl -X POST http://localhost:8000/api/quote \
  -H "Content-Type: application/json" \
  -d '{"age": 30, "gender": "Male", "sumInsured": 500000}'
```

## Docker

```bash
# Build image
docker build -t smarthealth-backend .

# Run container
docker run -p 8000:8000 -e OLLAMA_BASE_URL=http://host.docker.internal:11434 smarthealth-backend
```

<<<<<<< HEAD
Note: Adjust `OLLAMA_BASE_URL` to point to Ollama server accessible from container.
=======
Note: Adjust `OLLAMA_BASE_URL` to point to Ollama server accessible from container.
>>>>>>> 63441b0 (cost matrix included)
