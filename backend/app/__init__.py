import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

def create_app():
    app = Flask(__name__)

    cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
    CORS(app, resources={r"/api/*": {"origins": cors_origins, "supports_credentials": True}})

    from .routes.quote import bp as quote_bp
    from .routes.health import bp as health_bp

    app.register_blueprint(health_bp, url_prefix="/")
    app.register_blueprint(quote_bp, url_prefix="/api")

    return app