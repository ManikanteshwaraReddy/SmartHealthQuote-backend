#!/usr/bin/env python3
"""
Ingestion script to build FAISS index from CSV data.

Usage:
    python backend/scripts/ingest.py --csv backend/data/health_insurance_1part_4.csv --out backend/index
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np
from pathlib import Path

# Add parent directory to path to import modules
sys.path.append(str(Path(__file__).parent.parent))

from app.services.embedding import EmbeddingClient
from app.services.rag import RagIndex

def create_text_representation(row):
    """Create a text representation of a row for embedding."""
    parts = []
    
    # Add available fields to text representation
    if pd.notna(row.get('age')): parts.append(f"Age: {row['age']}")
    if pd.notna(row.get('gender')): parts.append(f"Gender: {row['gender']}")
    if pd.notna(row.get('location')): parts.append(f"Location: {row['location']}")
    if pd.notna(row.get('occupation')): parts.append(f"Occupation: {row['occupation']}")
    if pd.notna(row.get('medical_history')): parts.append(f"Medical History: {row['medical_history']}")
    if pd.notna(row.get('pre_existing_conditions')): parts.append(f"Pre-existing: {row['pre_existing_conditions']}")
    if pd.notna(row.get('lifestyle')): parts.append(f"Lifestyle: {row['lifestyle']}")
    if pd.notna(row.get('smoking_tobacco_use')): parts.append(f"Smoking: {row['smoking_tobacco_use']}")
    if pd.notna(row.get('alcohol_consumption')): parts.append(f"Alcohol: {row['alcohol_consumption']}")
    if pd.notna(row.get('exercise_frequency')): parts.append(f"Exercise: {row['exercise_frequency']}")
    if pd.notna(row.get('plan_type')): parts.append(f"Plan: {row['plan_type']}")
    if pd.notna(row.get('sum_insured')): parts.append(f"Sum Insured: {row['sum_insured']}")
    if pd.notna(row.get('premium_inr')): parts.append(f"Premium: ₹{row['premium_inr']}")
    
    return " | ".join(parts) if parts else "Health insurance record"

def main():
    parser = argparse.ArgumentParser(description="Build FAISS index from CSV")
    parser.add_argument("--csv", required=True, help="Path to CSV file")
    parser.add_argument("--out", required=True, help="Output directory for index")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.csv):
        print(f"Error: CSV file not found: {args.csv}")
        sys.exit(1)
    
    print(f"Loading CSV: {args.csv}")
    df = pd.read_csv(args.csv)
    print(f"Loaded {len(df)} rows")
    
    # Create text representations
    print("Creating text representations...")
    texts = []
    metadata = []
    
    for idx, row in df.iterrows():
        text = create_text_representation(row)
        texts.append(text)
        
        # Store metadata
        meta = {
            "id": idx,
            "text": text,
            "premium_inr": row.get('premium_inr') if pd.notna(row.get('premium_inr')) else None
        }
        
        # Add other relevant fields to metadata
        for col in ['age', 'gender', 'location', 'occupation', 'plan_type', 'sum_insured']:
            if col in df.columns and pd.notna(row.get(col)):
                meta[col] = row[col]
        
        metadata.append(meta)
    
    # Generate embeddings
    print("Generating embeddings...")
    embedder = EmbeddingClient()
    embeddings = embedder.embed_texts(texts)
    print(f"Generated embeddings shape: {embeddings.shape}")
    
    # Build FAISS index
    print("Building FAISS index...")
    rag = RagIndex()
    rag.build(embeddings, metadata)
    
    # Save index
    os.makedirs(args.out, exist_ok=True)
    index_path = os.path.join(args.out, "faiss.index")
    meta_path = os.path.join(args.out, "meta.json")
    
    print(f"Saving index to: {index_path}")
    print(f"Saving metadata to: {meta_path}")
    rag.save(index_path, meta_path)
    
    print("Done!")

if __name__ == "__main__":
    main()