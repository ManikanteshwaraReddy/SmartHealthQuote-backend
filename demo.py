#!/usr/bin/env python3
"""
Demo script showing the SmartHealthQuote backend functionality.
This demonstrates the API endpoints and key features.
"""

import sys
import json
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent / 'backend'))

def demo_api():
    """Demonstrate the API functionality"""
    print("🎯 SmartHealthQuote Backend Demo")
    print("=" * 40)
    
    from backend.app import create_app
    app = create_app()
    
    print("🏥 Starting Flask application...")
    
    with app.test_client() as client:
        # Test health endpoint
        print("\n📋 Testing Health Check Endpoint:")
        print("GET /health")
        response = client.get('/health')
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.get_json(), indent=2)}")
        
        # Test quote endpoint structure
        print("\n💰 Testing Quote Endpoint:")
        print("POST /api/quote")
        
        test_requests = [
            {
                "age": 30,
                "gender": "Male", 
                "location": "Mumbai",
                "medicalHistory": "No major issues",
                "lifestyle": "Active",
                "coverageNeed": "Comprehensive"
            },
            {
                "age": 35,
                "gender": "Female",
                "numberOfInsuredMembers": 3,
                "preExistingConditions": "Diabetes",
                "sumInsured": 1000000
            }
        ]
        
        for i, test_req in enumerate(test_requests, 1):
            print(f"\nTest Request {i}:")
            print(f"Data: {json.dumps(test_req, indent=2)}")
            
            response = client.post('/api/quote', json=test_req)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 500:
                error_data = response.get_json()
                if "FAISS index not found" in error_data.get("error", ""):
                    print("✅ Expected error: FAISS index not found (run ingestion first)")
                else:
                    print(f"❌ Unexpected error: {error_data}")
            else:
                print(f"Response: {json.dumps(response.get_json(), indent=2)}")

def demo_models():
    """Demonstrate the Pydantic models"""
    print("\n📊 Pydantic Models Demo")
    print("=" * 30)
    
    from backend.app.models.schemas import QuoteRequest, QuoteResponse, RetrievedContext
    
    # Demo QuoteRequest
    print("\n🔍 QuoteRequest Examples:")
    
    requests = [
        {"age": 30, "gender": "Male", "location": "Mumbai"},
        {"numberOfInsuredMembers": 2, "sumInsured": 500000, "planType": "Family"},
        {"age": 25, "preExistingConditions": "None", "smokingTobaccoUse": "No"}
    ]
    
    for i, req_data in enumerate(requests, 1):
        req = QuoteRequest(**req_data)
        print(f"Request {i}: {req_data}")
        print(f"  Parsed age: {req.age}")
        print(f"  Members: {req.number_of_insured_members}")
        print(f"  Sum insured: {req.sum_insured}")
    
    # Demo QuoteResponse
    print("\n📋 QuoteResponse Example:")
    context = RetrievedContext(
        id=1, 
        score=0.85, 
        snippet="Similar case: 30yr Male, Mumbai, Software Engineer",
        premium_inr=15000
    )
    
    response = QuoteResponse(
        planName="Comprehensive Health Plus",
        premiumINR=18500.0,
        sumInsured=750000,
        policyTermYears=1,
        paymentMode="Annual",
        deductibleINR=5000.0,
        coinsurancePercent=20.0,
        coverageDetails=[
            "Hospitalization expenses up to sum insured",
            "Pre and post hospitalization (30/60 days)", 
            "Emergency ambulance coverage",
            "Day care procedures",
            "Health checkup benefits"
        ],
        rationale="Premium calculated based on age, location, and health profile. Similar to cases in our database.",
        basedOnExamples=[context]
    )
    
    print("Generated Response:")
    print(json.dumps(response.model_dump(), indent=2))

def demo_file_structure():
    """Show the complete file structure"""
    print("\n📁 Project Structure")
    print("=" * 25)
    
    structure = """
SmartHealthQuote-backend/
├── README.md                    # Main project README
├── .gitignore                   # Git ignore rules
├── .env.example                 # Environment variables template
├── Dockerfile                   # Docker configuration
├── gunicorn.conf.py            # Gunicorn production config
├── test_backend.py             # Comprehensive test suite
└── backend/
    ├── README.md               # Backend-specific documentation
    ├── requirements.txt        # Python dependencies
    ├── __init__.py
    ├── app/
    │   ├── __init__.py         # Flask app factory
    │   ├── main.py             # Application entry point
    │   ├── models/
    │   │   ├── __init__.py
    │   │   └── schemas.py      # Pydantic request/response models
    │   ├── routes/
    │   │   ├── __init__.py
    │   │   ├── health.py       # Health check endpoint
    │   │   ├── quote.py        # Quote generation endpoint
    │   │   └── utils.py        # Route utilities and service getters
    │   └── services/
    │       ├── embedding.py    # Ollama embeddings client
    │       ├── llm.py          # Ollama LLM client  
    │       └── rag.py          # FAISS RAG implementation
    ├── scripts/
    │   └── ingest.py           # Data ingestion script
    └── data/
        └── health_insurance_1part_4.csv  # Sample data
    """
    print(structure)

def main():
    """Run the complete demo"""
    demo_file_structure()
    demo_models()
    demo_api()
    
    print("\n🎉 Demo Complete!")
    print("\n📝 Next Steps:")
    print("1. Install Ollama: curl -fsSL https://ollama.ai/install.sh | sh")
    print("2. Pull models: ollama pull mistral && ollama pull all-minilm")
    print("3. Run ingestion: python backend/scripts/ingest.py --csv backend/data/health_insurance_1part_4.csv --out backend/index")
    print("4. Start server: python -m backend.app.main")
    print("5. Test API: curl http://localhost:8000/health")

if __name__ == "__main__":
    main()