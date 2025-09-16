# Backend - SmartHealthQuote

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

```bash
# Ingest CSV data to build FAISS index
python backend/scripts/ingest.py --csv backend/data/health_insurance_1part_4.csv --out backend/index
```

This creates:
- `backend/index/faiss.index` - FAISS vector index
- `backend/index/meta.json` - Document metadata

### 5. Start the API Server

```bash
# Development mode
python -m backend.app.main

# Production mode with gunicorn
gunicorn -c gunicorn.conf.py backend.app.main:app
```

## API Endpoints

### Health Check
```bash
GET /health
```
Returns: `{"status": "ok"}`

### Quote Generation
```bash
POST /api/quote
Content-Type: application/json

{
  "age": 30,
  "gender": "Male",
  "location": "Mumbai",
  "occupation": "Software Engineer",
  "numberOfInsuredMembers": 2,
  "preExistingConditions": "None",
  "smokingTobaccoUse": "No",
  "sumInsured": 500000,
  "planType": "Individual"
}
```

Returns structured quote with:
- Plan details (name, premium, sum insured, etc.)
- Coverage details
- Rationale based on similar cases
- Retrieved context examples

## Models

### Ollama Models
- **Generation**: `mistral` (configurable via `GEN_MODEL`)
- **Embeddings**: `all-minilm` → maps to `all-MiniLM-L6-v2` sentence transformer (configurable via `EMBEDDING_MODEL`)

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

Note: Adjust `OLLAMA_BASE_URL` to point to Ollama server accessible from container.