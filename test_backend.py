#!/usr/bin/env python3
"""
Test script to verify the backend implementation meets acceptance criteria.
This tests the API without requiring Ollama to be running.
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent / 'backend'))

def test_basic_imports():
    """Test that all modules can be imported"""
    print("🔧 Testing imports...")
    
    try:
        from backend.app.models.schemas import QuoteRequest, QuoteResponse
        from backend.app.routes.health import bp as health_bp
        from backend.app.routes.quote import bp as quote_bp
        from backend.app.services.rag import RagIndex
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_flask_app():
    """Test Flask app creation and health endpoint"""
    print("🔧 Testing Flask application...")
    
    try:
        from backend.app import create_app
        app = create_app()
        
        with app.test_client() as client:
            # Test health endpoint
            response = client.get('/health')
            assert response.status_code == 200
            data = response.get_json()
            assert data == {"status": "ok"}
            print("✅ Health endpoint works")
            
            # Test quote endpoint structure (will fail without Ollama but should show proper error)
            response = client.post('/api/quote', 
                                 json={"age": 30, "gender": "Male", "location": "Mumbai"})
            # Should get 500 because FAISS index doesn't exist yet, which is expected
            assert response.status_code == 500
            data = response.get_json()
            assert "FAISS index not found" in data.get("error", "")
            print("✅ Quote endpoint structure works (expected FAISS error)")
            
        return True
    except Exception as e:
        print(f"❌ Flask app test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pydantic_models():
    """Test Pydantic model validation"""
    print("🔧 Testing Pydantic models...")
    
    try:
        from backend.app.models.schemas import QuoteRequest, QuoteResponse, RetrievedContext
        
        # Test QuoteRequest
        req = QuoteRequest(
            age=30,
            gender="Male",
            location="Mumbai",
            numberOfInsuredMembers=2,  # Test alias
            sumInsured=500000
        )
        assert req.age == 30
        assert req.number_of_insured_members == 2  # Test alias mapping
        assert req.sum_insured == 500000
        
        # Test age validation
        try:
            QuoteRequest(age=150)
            assert False, "Should have raised validation error"
        except ValueError:
            pass  # Expected
        
        # Test QuoteResponse
        context = RetrievedContext(id=1, score=0.8, snippet="Test", premium_inr=15000)
        response = QuoteResponse(
            planName="Test Plan",
            premiumINR=15000.0,
            coverageDetails=["Coverage 1"],
            rationale="Test rationale",
            basedOnExamples=[context]
        )
        assert response.planName == "Test Plan"
        assert len(response.basedOnExamples) == 1
        
        print("✅ Pydantic models work correctly")
        return True
    except Exception as e:
        print(f"❌ Pydantic test failed: {e}")
        return False

def test_csv_processing():
    """Test CSV loading and text representation"""
    print("🔧 Testing CSV processing...")
    
    try:
        import pandas as pd
        from backend.scripts.ingest import create_text_representation
        
        # Test with our sample CSV
        csv_path = Path(__file__).parent / 'backend/data/health_insurance_1part_4.csv'
        if not csv_path.exists():
            print(f"❌ Sample CSV not found: {csv_path}")
            return False
            
        df = pd.read_csv(csv_path)
        assert len(df) > 0
        
        # Test text representation
        text = create_text_representation(df.iloc[0])
        assert "Age: 25" in text
        assert "Gender: Male" in text
        assert "Mumbai" in text
        
        print("✅ CSV processing works")
        return True
    except Exception as e:
        print(f"❌ CSV processing test failed: {e}")
        return False

def test_faiss_rag():
    """Test FAISS RAG implementation with dummy data"""
    print("🔧 Testing FAISS RAG implementation...")
    
    try:
        import numpy as np
        from backend.app.services.rag import RagIndex
        
        # Create dummy embeddings and metadata
        embeddings = np.random.rand(5, 128).astype(np.float32)
        metadata = [
            {"id": i, "text": f"Sample text {i}", "premium_inr": 10000 + i * 1000}
            for i in range(5)
        ]
        
        # Test building index
        rag = RagIndex()
        rag.build(embeddings, metadata)
        
        # Test search
        query_embedding = np.random.rand(128).astype(np.float32)
        results = rag.search(query_embedding, top_k=3)
        
        assert len(results) == 3
        assert all("id" in r and "score" in r and "snippet" in r for r in results)
        
        # Test save/load with temporary files
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = os.path.join(tmpdir, "test.index")
            meta_path = os.path.join(tmpdir, "test.json")
            
            rag.save(index_path, meta_path)
            assert os.path.exists(index_path)
            assert os.path.exists(meta_path)
            
            # Test loading
            rag2 = RagIndex()
            rag2.load(index_path, meta_path)
            
            results2 = rag2.search(query_embedding, top_k=3)
            assert len(results2) == 3
        
        print("✅ FAISS RAG implementation works")
        return True
    except Exception as e:
        print(f"❌ FAISS RAG test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ingestion_script_structure():
    """Test that ingestion script has correct structure"""
    print("🔧 Testing ingestion script structure...")
    
    try:
        # Test that script can be imported
        from backend.scripts import ingest
        
        # Test that main function exists
        assert hasattr(ingest, 'main')
        assert hasattr(ingest, 'create_text_representation')
        
        # Test create_text_representation with sample data
        import pandas as pd
        sample_row = pd.Series({
            'age': 30,
            'gender': 'Male',
            'location': 'Mumbai',
            'premium_inr': 15000
        })
        
        text = ingest.create_text_representation(sample_row)
        assert "Age: 30" in text
        assert "Gender: Male" in text
        
        print("✅ Ingestion script structure is correct")
        return True
    except Exception as e:
        print(f"❌ Ingestion script test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Running SmartHealthQuote Backend Tests")
    print("=" * 50)
    
    tests = [
        test_basic_imports,
        test_pydantic_models,
        test_csv_processing,
        test_faiss_rag,
        test_flask_app,
        test_ingestion_script_structure,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
        print()
    
    print("=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Backend implementation is ready.")
        return True
    else:
        print("⚠️ Some tests failed. Check the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)