from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
import pymysql
import os

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

# 导入视图（确保在 db 初始化后导入以避免循环引用）
from wxcloudrun import views

# 创建数据库表（在应用上下文中）
with app.app_context():
    db.create_all()