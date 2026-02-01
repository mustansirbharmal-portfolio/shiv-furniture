from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import os

from app.config import Config
from app.database import init_db
from app.routes import register_routes

jwt = JWTManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Get allowed origins from environment
    allowed_origins = [
        app.config['FRONTEND_URL'], 
        "http://localhost:3000",
        "https://shiv-furniture-frontend-923410562127.europe-west1.run.app"
    ]
    
    # Add Cloud Run URLs if configured
    cloud_run_frontend = os.environ.get('CLOUD_RUN_FRONTEND_URL')
    if cloud_run_frontend:
        allowed_origins.append(cloud_run_frontend)
    
    # Allow all Google Cloud Run domains (*.run.app)
    CORS(app, resources={
        r"/api/*": {
            "origins": allowed_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True,
            "expose_headers": ["Content-Type", "Authorization"]
        }
    }, supports_credentials=True)
    
    jwt.init_app(app)
    
    init_db(app)
    
    register_routes(app)
    
    return app
