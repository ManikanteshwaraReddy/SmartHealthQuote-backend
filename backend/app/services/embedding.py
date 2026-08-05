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
# Public factory — same class name so callers don't change
# ─────────────────────────────────────────────────────────────────────────────

class EmbeddingClient:
    """Provider-agnostic embedding client.

    Delegates to either sentence-transformers (local) or Ollama based on
    the ``EMBEDDING_PROVIDER`` environment variable.
    """

    def __init__(self):
        provider = os.getenv("EMBEDDING_PROVIDER", "local").lower().strip()
        if provider == "ollama":
            self._backend = _OllamaEmbeddingBackend()
        elif provider == "local":
            self._backend = _LocalEmbeddingBackend()
        else:
            raise ValueError(
                f"Unknown EMBEDDING_PROVIDER '{provider}'. Use 'local' or 'ollama'."
            )
        logger.info("EmbeddingClient ready (provider=%s)", provider)

    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text."""
        return self._backend.embed_text(text)

    def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts."""
        return self._backend.embed_texts(texts)