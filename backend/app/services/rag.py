import os
import json
import faiss
import numpy as np
from typing import List, Dict, Any

class RagIndex:
    def __init__(self):
        self.index = None
        self.metadata = []
    
    def build(self, embeddings: np.ndarray, metadata: List[Dict[str, Any]]):
        """Build FAISS index from embeddings and metadata."""
        # Ensure embeddings are L2 normalized
        embeddings = embeddings.astype(np.float32)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / np.maximum(norms, 1e-8)
        
        # Create FAISS inner product index (equivalent to cosine similarity with normalized vectors)
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings)
        self.metadata = metadata
    
    def save(self, index_path: str, meta_path: str):
        """Save the FAISS index and metadata to disk."""
        if self.index is None:
            raise ValueError("No index to save. Build index first.")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(self.index, index_path)
        
        # Save metadata
        with open(meta_path, 'w') as f:
            json.dump(self.metadata, f, indent=2)
    
    def load(self, index_path: str, meta_path: str):
        """Load the FAISS index and metadata from disk."""
        if not os.path.exists(index_path):
            raise FileNotFoundError(f"Index file not found: {index_path}")
        if not os.path.exists(meta_path):
            raise FileNotFoundError(f"Metadata file not found: {meta_path}")
        
        # Load FAISS index
        self.index = faiss.read_index(index_path)
        
        # Load metadata
        with open(meta_path, 'r') as f:
            self.metadata = json.load(f)
    
    def search(self, query_embedding: np.ndarray, top_k: int = 8) -> List[Dict[str, Any]]:
        """Search for similar embeddings in the index."""
        if self.index is None:
            raise ValueError("No index loaded. Load or build index first.")
        
        # Ensure query embedding is normalized and has correct shape
        query_embedding = query_embedding.astype(np.float32)
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        # Normalize query embedding
        norm = np.linalg.norm(query_embedding)
        if norm > 0:
            query_embedding = query_embedding / norm
        
        # Search
        scores, indices = self.index.search(query_embedding, top_k)
        
        # Format results
        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx != -1:  # Valid result
                result = {
                    "id": int(idx),
                    "score": float(score),
                    "snippet": self.metadata[idx].get("text", ""),
                    "premium_inr": self.metadata[idx].get("premium_inr")
                }
                results.append(result)
        
        return results