"""
Embedding client with pluggable provider backends.

Supports two providers controlled by the ``EMBEDDING_PROVIDER`` environment variable:
  • **local**  – sentence-transformers (default, no API key needed)
  • **ollama** – Local Ollama instance (for local development)

The public interface (``embed_text``, ``embed_texts``) is identical
regardless of provider.
"""

from __future__ import annotations

import logging
import os
from typing import List

import numpy as np

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Local backend (sentence-transformers)
# ─────────────────────────────────────────────────────────────────────────────

class _LocalEmbeddingBackend:
    """Embedding backend using sentence-transformers (runs locally, no API key)."""

    def __init__(self):
        self.model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self._model = None  # lazy-loaded
        logger.info("Local embedding backend initialised (model=%s, lazy-load)", self.model_name)

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading sentence-transformers model: %s", self.model_name)
            self._model = SentenceTransformer(self.model_name)
            logger.info("Model loaded successfully (dimension=%s)", self._model.get_sentence_embedding_dimension())
        return self._model

    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts."""
        model = self._get_model()
        logger.debug("Embedding %d texts with sentence-transformers", len(texts))

        # sentence-transformers returns (N, dim) numpy array
        raw = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

        embeddings = []
        for emb in raw:
            emb = emb.astype(np.float32)
            # L2 normalize for inner product similarity (same as original)
            norm = np.linalg.norm(emb)
            if norm > 0:
                emb = emb / norm
            embeddings.append(emb)
        return embeddings


# ─────────────────────────────────────────────────────────────────────────────
# Ollama backend (local fallback)
# ─────────────────────────────────────────────────────────────────────────────

class _OllamaEmbeddingBackend:
    """Embedding backend using a local Ollama instance (original implementation)."""

    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("EMBEDDING_MODEL", "all-minilm")
        logger.info("Ollama embedding backend initialised (url=%s, model=%s)", self.base_url, self.model)

    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts."""
        import requests

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
                    "or the endpoint is disabled. Please upgrade Ollama and pull an embeddings model "
                    "(e.g., `ollama pull all-minilm` or `ollama pull nomic-embed-text`)."
                )

            response.raise_for_status()

            embedding = np.array(response.json()["embedding"], dtype=np.float32)
            # L2 normalize the embedding for inner product similarity
            embedding = embedding / np.linalg.norm(embedding)
            embeddings.append(embedding)

        return embeddings


# ─────────────────────────────────────────────────────────────────────────────
# Voyage AI backend
# ─────────────────────────────────────────────────────────────────────────────

class _VoyageEmbeddingBackend:
    """Embedding backend using Voyage AI API."""

    def __init__(self):
        import voyageai
        
        self.api_key = os.getenv("VOYAGE_API_KEY")
        if not self.api_key:
            logger.warning("VOYAGE_API_KEY not found in environment!")
            
        self.client = voyageai.Client(api_key=self.api_key)
        self.model = os.getenv("EMBEDDING_MODEL", "voyage-3-lite")
        logger.info("Voyage embedding backend initialised (model=%s)", self.model)

    def embed_text(self, text: str) -> np.ndarray:
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        import time
        
        embeddings = []
        # Voyage AI typically supports batching up to 128 documents per request
        batch_size = 120
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            # Retry logic for rate limits
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    result = self.client.embed(
                        batch_texts,
                        model=self.model
                    )
                    break
                except Exception as e:
                    if "429" in str(e) or "Rate limit" in str(e):
                        if attempt == max_retries - 1:
                            raise
                        logger.warning(f"Rate limited by Voyage API. Retrying in {2 ** attempt}s...")
                        time.sleep(2 ** attempt)
                    else:
                        raise
            
            for raw_emb in result.embeddings:
                emb = np.array(raw_emb, dtype=np.float32)
                # L2 normalize
                norm = np.linalg.norm(emb)
                if norm > 0:
                    emb = emb / norm
                embeddings.append(emb)
                
            # Add a small delay between batches
            time.sleep(0.1)
            
        return embeddings


# ─────────────────────────────────────────────────────────────────────────────
# Public factory — same class name so callers don't change
# ─────────────────────────────────────────────────────────────────────────────

class EmbeddingClient:
    """Provider-agnostic embedding client.

    Delegates to either sentence-transformers (local) or Ollama based on
    the ``EMBEDDING_PROVIDER`` environment variable.
    """

    def __init__(self):
        provider = os.getenv("EMBEDDING_PROVIDER", "voyage").lower().strip()
        if provider == "ollama":
            self._backend = _OllamaEmbeddingBackend()
        elif provider == "local":
            self._backend = _LocalEmbeddingBackend()
        elif provider == "voyage":
            self._backend = _VoyageEmbeddingBackend()
        else:
            raise ValueError(
                f"Unknown EMBEDDING_PROVIDER '{provider}'. Use 'voyage', 'local', or 'ollama'."
            )
        logger.info("EmbeddingClient ready (provider=%s)", provider)

    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        return self._backend.embed_text(text)

    def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts."""
        return self._backend.embed_texts(texts)