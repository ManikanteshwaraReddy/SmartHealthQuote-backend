import os
import requests
import numpy as np
from typing import List

class EmbeddingClient:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("EMBEDDING_MODEL", "all-minilm")
    
    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text"""
        embeddings = self.embed_texts([text])
        return embeddings[0]
    
    def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts"""
        embeddings = []
        
        for text in texts:
            try:
                response = requests.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": self.model,
                        "prompt": text
                    },
                    timeout=30
                )
            except requests.exceptions.RequestException as e:
                raise RuntimeError(
                    f"Failed to reach Ollama embeddings endpoint at {self.base_url}/api/embeddings. "
                    f"Ensure Ollama is running and accessible. Original error: {e}"
                ) from e

            # Provide clearer guidance if the server doesn't support embeddings
            if response.status_code == 404:
                raise RuntimeError(
                    "Ollama server returned 404 for /api/embeddings. Your Ollama version may not support embeddings, "
                    "or the endpoint is disabled. Please upgrade Ollama and pull an embeddings model (e.g., `ollama pull all-minilm` or `ollama pull nomic-embed-text`)."
                )

            response.raise_for_status()
            
            embedding = np.array(response.json()["embedding"], dtype=np.float32)
            # L2 normalize the embedding for inner product similarity
            embedding = embedding / np.linalg.norm(embedding)
            embeddings.append(embedding)
        
        return embeddings