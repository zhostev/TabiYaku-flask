# wxcloudrun/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api
from flask_jwt_extended import JWTManager
import pymysql
import logging
import sys

# 因 MySQLdb 不支持 Python3，使用 pymysql 作为替代
pymysql.install_as_MySQLdb()

# 初始化 Flask 应用
app = Flask(__name__)

# 加载配置
app.config.from_object('wxcloudrun.config.Config')

# 初始化日志
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# 初始化数据库
db = SQLAlchemy(app)

# 初始化 JWT
jwt = JWTManager(app)

# 初始化 Flask-RESTful
api = Api(app)

# 导入并注册视图 Blueprint
from .views import main_bp
app.register_blueprint(main_bp)

# 导入 API 资源类
from .resources import (
    UserRegister,
    UserLogin,
    ImageUpload,
    TranslationRecordResource,
    TranslationRecordsListResource,
    UserLogout
)

# 注册 API 资源，指定唯一的 endpoint 名称
api.add_resource(UserRegister, '/api/register', endpoint="user_register")
api.add_resource(UserLogin, '/api/login', endpoint="user_login")
api.add_resource(ImageUpload, '/api/upload_image', endpoint="image_upload")
api.add_resource(TranslationRecordResource, '/api/translation/<int:record_id>', endpoint="translation_record")
api.add_resource(TranslationRecordsListResource, '/api/records', endpoint="translation_records_list")
api.add_resource(UserLogout, '/api/logout', endpoint="user_logout")  # 可选

# 创建数据库表
with app.app_context():
    db.create_all()
    logger.info("数据库表创建完成")