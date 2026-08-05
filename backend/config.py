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
    # RAG / AI
    # ------------------------------------------------------------------ #
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    GEN_MODEL: str = os.getenv("GEN_MODEL", "mistral")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-minilm")
    INDEX_DIR: str = os.getenv("INDEX_DIR", "backend/index")
    TOP_K: int = int(os.getenv("TOP_K", "8"))
    USE_LLM_FOR_AMOUNT: bool = os.getenv("USE_LLM_FOR_AMOUNT", "true").lower() in (
        "1",
        "true",
        "yes",
    )
