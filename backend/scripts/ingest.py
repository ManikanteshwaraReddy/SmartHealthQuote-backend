#!/usr/bin/env python3
"""
CSV ingestion script to build FAISS index for RAG.
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np
from pathlib import Path

# Add backend to Python path to import our modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.embedding import EmbeddingClient
from app.services.rag import RagIndex

def build_text_representation(row) -> str:
    """Build a text representation of an insurance record for embedding"""
    parts = []
    
    # Basic demographics
    if pd.notna(row.get('Age')): parts.append(f"Age: {row['Age']}")
    if pd.notna(row.get('Gender')): parts.append(f"Gender: {row['Gender']}")
    if pd.notna(row.get('Location')): parts.append(f"Location: {row['Location']}")
    if pd.notna(row.get('Occupation')): parts.append(f"Occupation: {row['Occupation']}")
    
    # Family details
    if pd.notna(row.get('Number_of_Insured_Members')): parts.append(f"Family size: {row['Number_of_Insured_Members']}")
    if pd.notna(row.get('Family_Details')): parts.append(f"Family details: {row['Family_Details']}")
    
    # Health information
    if pd.notna(row.get('Pre_existing_Conditions')): parts.append(f"Pre-existing conditions: {row['Pre_existing_Conditions']}")
    if pd.notna(row.get('Past_Medical_History')): parts.append(f"Past medical history: {row['Past_Medical_History']}")
    if pd.notna(row.get('Family_Medical_History')): parts.append(f"Family medical history: {row['Family_Medical_History']}")
    
    # Physical details
    if pd.notna(row.get('Height_cm')) and pd.notna(row.get('Weight_kg')):
        bmi = row['Weight_kg'] / ((row['Height_cm'] / 100) ** 2)
        parts.append(f"BMI: {bmi:.1f}")
    
    # Lifestyle
    if pd.notna(row.get('Pregnancy_Status')): parts.append(f"Pregnancy status: {row['Pregnancy_Status']}")
    if pd.notna(row.get('Smoking_Tobacco_Use')): parts.append(f"Smoking/tobacco: {row['Smoking_Tobacco_Use']}")
    if pd.notna(row.get('Alcohol_Consumption')): parts.append(f"Alcohol: {row['Alcohol_Consumption']}")
    if pd.notna(row.get('Exercise_Frequency')): parts.append(f"Exercise: {row['Exercise_Frequency']}")
    
    # Insurance details
    if pd.notna(row.get('Plan_Type')): parts.append(f"Plan type: {row['Plan_Type']}")
    if pd.notna(row.get('Sum_Insured')): parts.append(f"Sum insured: ₹{row['Sum_Insured']}")
    if pd.notna(row.get('Policy_Term_Years')): parts.append(f"Policy term: {row['Policy_Term_Years']} years")
    if pd.notna(row.get('Premium_Payment_Mode')): parts.append(f"Payment mode: {row['Premium_Payment_Mode']}")
    if pd.notna(row.get('Premium_INR')): parts.append(f"Premium: ₹{row['Premium_INR']}")
    
    return "; ".join(parts) if parts else "Insurance record"

def ingest_csv(csv_path: str, output_dir: str, limit: int | None = None) -> None:
    """Ingest CSV file and create FAISS index"""
    
    # Load CSV
    print(f"Loading CSV from: {csv_path}")
    df = pd.read_csv(csv_path)
    if limit is not None and limit > 0:
        print(f"Limiting to first {limit} rows for ingestion preview")
        df = df.head(limit)
    print(f"Loaded {len(df)} records")
    
    # Initialize services
    print("Initializing embedding client...")
    embedder = EmbeddingClient()
    
    print("Creating text representations...")
    texts = []
    metadata = []
    
    for idx, row in df.iterrows():
        text = build_text_representation(row)
        texts.append(text)
        
        # Create metadata entry
        meta = {
            "text": text,
            "row_id": idx,
        }
        
        # Add all available fields to metadata
        for col in df.columns:
            if pd.notna(row[col]):
                # Convert column name to snake_case for consistency
                key = col.lower().replace(' ', '_')
                meta[key] = row[col]
        
        metadata.append(meta)
    
    print(f"Generated {len(texts)} text representations")
    
    # Generate embeddings
    print("Generating embeddings...")
    embeddings = embedder.embed_texts(texts)
    embeddings_array = np.array(embeddings)
    print(f"Generated embeddings with shape: {embeddings_array.shape}")
    
    # Create RAG index
    print("Creating FAISS index...")
    rag = RagIndex()
    rag.add_documents(embeddings_array, metadata)
    
    # Save index
    os.makedirs(output_dir, exist_ok=True)
    index_path = os.path.join(output_dir, "faiss.index")
    meta_path = os.path.join(output_dir, "meta.json")
    
    print(f"Saving index to: {index_path}")
    print(f"Saving metadata to: {meta_path}")
    rag.save(index_path, meta_path)
    
    # Print stats
    stats = rag.get_stats()
    print(f"Index created successfully!")
    print(f"Total vectors: {stats['total_vectors']}")
    print(f"Dimension: {stats['dimension']}")
    print(f"Metadata entries: {stats['metadata_count']}")

def main():
    parser = argparse.ArgumentParser(description="Ingest CSV and build FAISS index")
    parser.add_argument("--csv", required=True, help="Path to CSV file")
    parser.add_argument("--out", required=True, help="Output directory for index files")
    parser.add_argument("--limit", type=int, default=None, help="Optional: only ingest first N rows for a quick test")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.csv):
        print(f"Error: CSV file not found: {args.csv}")
        sys.exit(1)
    
    try:
        ingest_csv(args.csv, args.out, limit=args.limit)
        print("Ingestion completed successfully!")
    except Exception as e:
        print(f"Error during ingestion: {e}")
        print("\nTroubleshooting:")
        print("- Ensure Ollama is running and accessible at OLLAMA_BASE_URL (default http://localhost:11434)")
        print("- Upgrade Ollama if /api/embeddings returns 404: https://ollama.ai")
        print("- Pull an embeddings model, e.g.: `ollama pull all-minilm` or `ollama pull nomic-embed-text`")
        print("- Try a quick smoke test with a small subset: --limit 100")
        sys.exit(1)

if __name__ == "__main__":
    main()