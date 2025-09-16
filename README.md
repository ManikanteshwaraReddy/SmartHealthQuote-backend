# SmartHealthQuote Backend

Flask backend for health insurance quotation using RAG (Retrieval-Augmented Generation) with Ollama and FAISS.

## Architecture

- **Flask API** with CORS support
- **Pydantic** for request/response validation
- **Ollama** for LLM generation (mistral) and embeddings (all-minilm → all-MiniLM-L6-v2)
- **FAISS** for vector similarity search with inner-product index
- **RAG flow**: CSV ingestion → FAISS index → quotation API

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Install and Setup Ollama

```bash
# Install Ollama (see https://ollama.ai)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull required models
ollama pull mistral
ollama pull all-minilm
```

Note: `all-minilm` in Ollama maps to the `all-MiniLM-L6-v2` sentence transformer model.

### 3. Environment Configuration

Copy `.env.example` to `.env` and adjust as needed:

```bash
cp ../.env.example ../.env
```

Key environment variables:
- `OLLAMA_BASE_URL`: Ollama API endpoint (default: http://localhost:11434)
- `GEN_MODEL`: LLM model for generation (default: mistral)
- `EMBEDDING_MODEL`: Model for embeddings (default: all-minilm)
- `INDEX_DIR`: Directory for FAISS index files (default: backend/index)
- `TOP_K`: Number of similar examples to retrieve (default: 8)

### 4. Data Ingestion

Place your CSV file in `backend/data/` and run ingestion:

```bash
# Create sample data directory (optional)
mkdir -p data

# Run ingestion to build FAISS index
python scripts/ingest.py --csv data/health_insurance_1part_4.csv --out index
```

Expected CSV columns (flexible schema):
- `age`, `gender`, `location`, `occupation`
- `medical_history`, `pre_existing_conditions`, `lifestyle`
- `smoking_tobacco_use`, `alcohol_consumption`, `exercise_frequency`
- `plan_type`, `sum_insured`, `premium_inr`

## Running the API

### Development Mode

```bash
python -m app.main
```

Server will start on http://localhost:8000

### Production Mode

```bash
gunicorn -c ../gunicorn.conf.py app.main:app
```

## API Endpoints

### Health Check
```bash
GET /health
Response: {"status": "ok"}
```

### Quote Generation
```bash
POST /api/quote
Content-Type: application/json

{
  "age": 30,
  "gender": "Male",
  "location": "Mumbai",
  "medicalHistory": "No major issues",
  "lifestyle": "Active",
  "coverageNeed": "Comprehensive"
}
```

Response includes:
- `planName`: Recommended insurance plan
- `premiumINR`: Annual premium amount
- `coverageDetails`: List of covered benefits
- `rationale`: Explanation of the quote
- `basedOnExamples`: Similar cases used for reference

## Docker Deployment

```bash
# Build image
docker build -t smarthealth-backend .

# Run container
docker run -p 8000:8000 -e OLLAMA_BASE_URL=http://host.docker.internal:11434 smarthealth-backend
```

## Development

### Project Structure

```
backend/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── main.py              # Application entry point
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py       # Pydantic models
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── health.py        # Health check endpoint
│   │   ├── quote.py         # Quote generation endpoint
│   │   └── utils.py         # Route utilities
│   └── services/
│       ├── embedding.py     # Ollama embeddings client
│       ├── llm.py          # Ollama LLM client
│       └── rag.py          # FAISS RAG implementation
├── scripts/
│   └── ingest.py           # Data ingestion script
└── requirements.txt        # Python dependencies
```

### Testing

Basic smoke test:

```bash
# Start the server
python -m app.main

# Test health endpoint
curl http://localhost:8000/health

# Test quote endpoint
curl -X POST http://localhost:8000/api/quote \
  -H "Content-Type: application/json" \
  -d '{"age": 30, "gender": "Male", "medicalHistory": "Good health"}'
```
