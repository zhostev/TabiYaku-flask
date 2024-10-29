# app/__init__.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_cors import CORS
from flask_restx import Api
from config import *
import os
from dotenv import load_dotenv
 
load_dotenv()  # Load environment variables from .env
 
db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()
api = Api(
    title='TabiYaku API',
    version='1.0',
    description='API documentation for TabiYaku',
)
 
def create_app():
    app = Flask(__name__)
    app.config.from_object('config')
     
    # Initialize Extensions
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    api.init_app(app)
     
    # Create upload folder if not exists with error handling
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    except PermissionError:
        app.logger.error(f"Permission denied while creating directory: {app.config['UPLOAD_FOLDER']}")
        raise
     
    # Register Namespaces
    from app.routes.auth import auth_ns
    from app.routes.translate import translate_ns
    api.add_namespace(auth_ns, path='/api/auth')
    api.add_namespace(translate_ns, path='/api')
     
    return app