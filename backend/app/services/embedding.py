import os
import requests
import numpy as np
from typing import List

class EmbeddingClient:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("EMBEDDING_MODEL", "all-minilm")
    
    def embed_text(self, text: str) -> np.ndarray:
        """Generate embeddings for a single text."""
        url = f"{self.base_url}/api/embeddings"
        payload = {
            "model": self.model,
            "prompt": text
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        embedding = np.array(data["embedding"], dtype=np.float32)
        
        # L2 normalize the embedding
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
            
        return embedding
    
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            embedding = self.embed_text(text)
            embeddings.append(embedding)
        
        return np.array(embeddings)