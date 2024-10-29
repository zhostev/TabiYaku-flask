# app/__init__.py

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_cors import CORS
from flask_restx import Api
from config import *
from dotenv import load_dotenv

load_dotenv()  # 加载 .env 文件中的环境变量

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

    # 初始化扩展
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    api.init_app(app)

    # 创建上传文件夹，如果不存在则创建，并处理权限错误
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    except PermissionError:
        app.logger.error(f"Permission denied while creating directory: {app.config['UPLOAD_FOLDER']}")
        raise

    # 导入所有命名空间和模型
    from app.routes import auth_ns, translate_ns, users_ns
    from app import models  # 确保模型被导入

    # 注册命名空间
    api.add_namespace(auth_ns, path='/api/auth')
    api.add_namespace(translate_ns, path='/api/translate')
    api.add_namespace(users_ns, path='/api/users')  # 注册 users 命名空间

    return app