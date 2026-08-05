"""
Application configuration.

All values are read from environment variables (loaded from .env by create_app).
Import Config or use current_app.config after the app is created.
"""
from __future__ import annotations

import os
from typing import List


class Config:
    # ------------------------------------------------------------------ #
    # Flask
    # ------------------------------------------------------------------ #
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    DEBUG: bool = os.getenv("FLASK_DEBUG", "false").lower() in ("1", "true", "yes")

    # ------------------------------------------------------------------ #
    # CORS
    # ------------------------------------------------------------------ #
    CORS_ORIGINS: List[str] = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
        if o.strip()
    ]

    # ------------------------------------------------------------------ #
    # MongoDB
    # ------------------------------------------------------------------ #
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "smarthealthquote")

    # ------------------------------------------------------------------ #
    # JWT
    # ------------------------------------------------------------------ #
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-jwt-secret-in-production")
    JWT_REFRESH_SECRET: str = os.getenv(
        "JWT_REFRESH_SECRET", "change-refresh-secret-in-production"
    )
    ACCESS_TOKEN_EXPIRY_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRY_MINUTES", "15")
    )
    REFRESH_TOKEN_EXPIRY_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRY_DAYS", "7"))

    # ------------------------------------------------------------------ #
    # Security
    # ------------------------------------------------------------------ #
    BCRYPT_ROUNDS: int = int(os.getenv("BCRYPT_ROUNDS", "12"))

    # ------------------------------------------------------------------ #
    # Rate limiting
    # ------------------------------------------------------------------ #
    RATELIMIT_DEFAULT: str = os.getenv("RATELIMIT_DEFAULT", "200 per day;50 per hour")
    RATELIMIT_AUTH: str = os.getenv("RATELIMIT_AUTH", "10 per minute")
    RATELIMIT_STORAGE_URI: str = os.getenv("RATELIMIT_STORAGE_URI", "memory://")

    # ------------------------------------------------------------------ #
    # LLM Provider: "groq" (cloud, default) or "ollama" (local fallback)
    # ------------------------------------------------------------------ #
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq")

    # Groq settings (used when LLM_PROVIDER=groq)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # Ollama settings (used when LLM_PROVIDER=ollama)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    GEN_MODEL: str = os.getenv("GEN_MODEL", "mistral")

    # -- Embeddings --
    # Options: "local", "ollama", "voyage"
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "voyage")
    
    # Provider-specific models
    # "voyage-3-lite" for voyage
    # "all-MiniLM-L6-v2" for local
    # "all-minilm" for ollama
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "voyage-3-lite")
    
    VOYAGE_API_KEY: str = os.getenv("VOYAGE_API_KEY", "")

    # ------------------------------------------------------------------ #
    # RAG
    # ------------------------------------------------------------------ #
    INDEX_DIR: str = os.getenv("INDEX_DIR", "backend/index")
    TOP_K: int = int(os.getenv("TOP_K", "8"))
    USE_LLM_FOR_AMOUNT: bool = os.getenv("USE_LLM_FOR_AMOUNT", "true").lower() in (
        "1",
        "true",
        "yes",
    )
