"""
Application factory.

create_app() wires together:
  - Configuration
  - CORS
  - Rate limiter
  - MongoDB
  - All blueprints

Keep this file free of business logic — it is purely infrastructure setup.
"""
from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()

# Module-level limiter — initialised without app; attached in create_app().
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
)

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)

    # ── Config ──────────────────────────────────────────────────────────────
    from backend.config import Config
    app.config.from_object(Config)

    # Promote selected config values to top-level for flask-limiter compat.
    app.config["RATELIMIT_STORAGE_URI"] = Config.RATELIMIT_STORAGE_URI

    # ── Logging ─────────────────────────────────────────────────────────────
    logging.basicConfig(
        level=logging.DEBUG if Config.DEBUG else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # ── CORS ────────────────────────────────────────────────────────────────
    CORS(
        app,
        resources={r"/*": {"origins": Config.CORS_ORIGINS}},
        supports_credentials=True,
    )

    # ── Rate limiter ─────────────────────────────────────────────────────────
    limiter.init_app(app)

    # ── MongoDB ──────────────────────────────────────────────────────────────
    try:
        from backend.app.database.connection import init_db
        init_db(Config.MONGO_URI, Config.DATABASE_NAME)
    except Exception as exc:
        # Log but don't crash — app can serve requests without DB
        # (quote generation is stateless).  Auth routes will return 500
        # when they attempt DB access.
        logger.warning("MongoDB connection failed at startup: %s", exc)

    # ── Blueprints ───────────────────────────────────────────────────────────
    from backend.app.auth.routes import bp as auth_bp
    from backend.app.quotes.routes import quote_bp, health_bp

    # Apply auth rate-limit to login and register
    limiter.limit(Config.RATELIMIT_AUTH)(auth_bp)

    app.register_blueprint(health_bp, url_prefix="/")
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(quote_bp, url_prefix="/api")

    logger.info("SmartHealthQuote backend started.")
    return app