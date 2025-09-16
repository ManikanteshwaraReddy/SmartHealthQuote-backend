import os
import json
import numpy as np
import faiss
from typing import List, Dict, Any, Optional

class RagIndex:
    def __init__(self):
        self.index: Optional[faiss.Index] = None
        self.metadata: List[Dict[str, Any]] = []
        self.dimension = 384  # all-MiniLM-L6-v2 embedding dimension
    
    def create_index(self, embeddings: np.ndarray) -> None:
        """Create a new FAISS index with inner product similarity"""
        self.dimension = embeddings.shape[1]
        # Use inner product index for L2-normalized vectors (equivalent to cosine similarity)
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(embeddings.astype(np.float32))
    
    def add_documents(self, embeddings: np.ndarray, metadata: List[Dict[str, Any]]) -> None:
        """Add documents to existing index"""
        if self.index is None:
            self.create_index(embeddings)
        else:
            self.index.add(embeddings.astype(np.float32))
        self.metadata.extend(metadata)
    
    def search(self, query_embedding: np.ndarray, top_k: int = 8) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        if self.index is None:
            raise ValueError("Index not loaded. Call load() first.")
        
        # Ensure query embedding is 2D and normalized
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        # Search the index
        scores, indices = self.index.search(query_embedding.astype(np.float32), top_k)
        
        results = []
        for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
            if idx != -1:  # Valid result
                result = {
                    "id": int(idx),
                    "score": float(score),
                    "text": self.metadata[idx].get("text", ""),
                    **self.metadata[idx]  # Include all metadata
                }
                results.append(result)
        
        return results
    
    def save(self, index_path: str, meta_path: str) -> None:
        """Save index and metadata to files"""
        if self.index is None:
            raise ValueError("No index to save")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(index_path), exist_ok=True)
        os.makedirs(os.path.dirname(meta_path), exist_ok=True)
        
        # Save FAISS index
        faiss.write_index(self.index, index_path)
        
        # Save metadata
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)
    
    def load(self, index_path: str, meta_path: str) -> None:
        """Load index and metadata from files"""
        if not os.path.exists(index_path):
            raise FileNotFoundError(f"Index file not found: {index_path}")
        if not os.path.exists(meta_path):
            raise FileNotFoundError(f"Metadata file not found: {meta_path}")
        
        # Load FAISS index
        self.index = faiss.read_index(index_path)
        
        # Load metadata
        with open(meta_path, 'r', encoding='utf-8') as f:
            self.metadata = json.load(f)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        if self.index is None:
            return {"status": "not_loaded"}
        
        return {
            "status": "loaded",
            "total_vectors": self.index.ntotal,
            "dimension": self.index.d,
            "metadata_count": len(self.metadata)
        }