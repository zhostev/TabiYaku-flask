# wxcloudrun/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api
from flask_jwt_extended import JWTManager
import pymysql

# 因 MySQLdb 不支持 Python3，使用 pymysql 替代
pymysql.install_as_MySQLdb()

# 初始化 Flask 应用
app = Flask(__name__)

# 加载配置
app.config.from_object('wxcloudrun.config.Config')

# 初始化数据库
db = SQLAlchemy(app)

# 初始化 JWT
jwt = JWTManager(app)

# 初始化 Flask-RESTful
api = Api(app)

# 导入并注册视图 Blueprint
from .views import main_bp
app.register_blueprint(main_bp)

# 导入并注册 API 资源
from .views import (
    ImageUpload,
    TranslationRecordResource,
    UserRegister,
    UserLogin,
    UserLogout,
    TranslationRecordsListResource
)

api.add_resource(UserRegister, '/api/register')
api.add_resource(UserLogin, '/api/login')
api.add_resource(ImageUpload, '/api/upload_image')
api.add_resource(TranslationRecordResource, '/api/translation/<int:record_id>')
api.add_resource(TranslationRecordsListResource, '/api/records')
api.add_resource(UserLogout, '/api/logout')  # 可选

# 创建数据库表
with app.app_context():
    db.create_all()