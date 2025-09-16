#!/bin/bash

# Setup script for SmartHealthQuote backend
set -e

echo "🔧 Setting up SmartHealthQuote Backend..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

echo "✓ Python 3 found"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Check if Ollama is available
if ! command -v ollama &> /dev/null; then
    echo "⚠️  Ollama not found. Please install Ollama from https://ollama.ai"
    echo "   After installation, run:"
    echo "   ollama pull mistral"
    echo "   ollama pull all-minilm"
else
    echo "✓ Ollama found"
    echo "📥 Pulling required models..."
    ollama pull mistral
    ollama pull all-minilm
fi

# Create directories
echo "📁 Creating directories..."
mkdir -p backend/index
mkdir -p backend/data

# Copy environment file
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✓ Created .env from .env.example"
else
    echo "✓ .env already exists"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Add your CSV data to backend/data/"
echo "2. Run ingestion: python backend/scripts/ingest.py --csv backend/data/your_file.csv --out backend/index"
echo "3. Start the server: python -m backend.app.main"
echo ""
echo "For more information, see backend/README.md"