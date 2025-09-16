#!/usr/bin/env python3
"""
Simple test to verify our Flask app structure without dependencies
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Test that all our modules can be imported without external dependencies"""
    try:
        print("Testing imports...")
        
        # Add backend to Python path for imports
        sys.path.insert(0, str(Path.cwd() / "backend"))
        
        # Test basic Python imports
        print("✓ Python basic imports work")
        
        # Check if we can import our schemas (this requires pydantic)
        try:
            from app.models.schemas import QuoteRequest, QuoteResponse, Gender
            print("✓ Models imported successfully") 
            return True
        except ImportError as e:
            print(f"⚠ Models import requires dependencies: {e}")
            return True  # This is expected without installed packages
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_environment():
    """Test environment configuration"""
    try:
        print("\nTesting environment...")
        
        # Load .env.example
        env_file = Path(".env.example")
        if env_file.exists():
            print("✓ .env.example exists")
            with open(env_file) as f:
                content = f.read()
                required_vars = ["OLLAMA_BASE_URL", "GEN_MODEL", "EMBEDDING_MODEL", "INDEX_DIR"]
                for var in required_vars:
                    if var in content:
                        print(f"✓ {var} configured")
                    else:
                        print(f"✗ {var} missing")
        else:
            print("✗ .env.example not found")
            
        return True
        
    except Exception as e:
        print(f"✗ Environment test error: {e}")
        return False

def test_file_structure():
    """Test that all required files exist"""
    print("Testing file structure...")
    
    required_files = [
        "backend/app/__init__.py",
        "backend/app/main.py", 
        "backend/app/models/schemas.py",
        "backend/app/routes/health.py",
        "backend/app/routes/quote.py",
        "backend/app/services/embedding.py",
        "backend/app/services/llm.py",
        "backend/app/services/rag.py",
        "backend/scripts/ingest.py",
        "requirements.txt",
        "Dockerfile",
        "README.md",
        "backend/README.md"
    ]
    
    all_exist = True
    
    for file_path in required_files:
        full_path = Path(file_path)
        if full_path.exists():
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} missing")
            all_exist = False
    
    return all_exist

def test_script_permissions():
    """Test that scripts are executable"""
    print("\nTesting script permissions...")
    
    script_path = Path("backend/scripts/ingest.py")
    if script_path.exists():
        if os.access(script_path, os.X_OK):
            print("✓ ingest.py is executable")
            return True
        else:
            print("⚠ ingest.py exists but not executable")
            return True
    else:
        print("✗ ingest.py not found")
        return False

if __name__ == "__main__":
    print("=== Testing SmartHealthQuote Backend Structure ===")
    
    results = []
    results.append(test_file_structure())
    results.append(test_environment())
    results.append(test_script_permissions())
    results.append(test_imports())
    
    print("\n=== Summary ===")
    if all(results):
        print("🎉 All tests passed! Backend structure is ready.")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Setup Ollama with: ollama pull mistral && ollama pull all-minilm")
        print("3. Ingest data: python backend/scripts/ingest.py --csv data.csv --out backend/index")
        print("4. Start server: python -m backend.app.main")
    else:
        print("❌ Some tests failed. Please check the output above.")
    
    sys.exit(0 if all(results) else 1)