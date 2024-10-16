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

# 导入并注册 API 资源
from .views import ImageUpload, TranslationRecordResource, UserRegister, UserLogin

api.add_resource(UserRegister, '/register')
api.add_resource(UserLogin, '/login')
api.add_resource(ImageUpload, '/upload_image')
api.add_resource(TranslationRecordResource, '/records/<int:record_id>')

# 创建数据库表
with app.app_context():
    db.create_all()