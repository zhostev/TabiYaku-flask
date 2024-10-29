# wxcloudrun/__init__.py

from apiflask import APIFlask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
import pymysql
import logging
import sys
from flask import jsonify
from flask_migrate import Migrate


# Install pymysql as MySQLdb, since MySQLdb doesn't support Python 3
pymysql.install_as_MySQLdb()

# Initialize APIFlask app
app = APIFlask(__name__, docs_ui='swagger-ui')

# Load configuration from 'backend.config.Config'
app.config.from_object('backend.config.Config')

# Initialize logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# Initialize SQLAlchemy
db = SQLAlchemy(app)
migrate = Migrate(app, db)


# Initialize JWT Manager
jwt = JWTManager(app)

# Import and register APIBlueprint
from .resources import main_bp  # 确保路径正确
app.register_blueprint(main_bp)

# Define error handlers to ensure all errors return JSON responses
@app.errorhandler(400)
@app.errorhandler(401)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(500)
def handle_error(e):
    return jsonify({'message': str(e)}), e.code if hasattr(e, 'code') else 500

# Create database tables
with app.app_context():
    db.create_all()
    logger.info("数据库表创建完成")