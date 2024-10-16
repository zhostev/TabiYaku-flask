from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import pymysql
import os
import logging

# 因 MySQLdb 不支持 Python3，使用 pymysql 替代
pymysql.install_as_MySQLdb()

# 初始化 web 应用
app = Flask(__name__)

# 加载配置
app.config.from_object('wxcloudrun.config.Config')

# 初始化数据库
db = SQLAlchemy(app)

# 配置日志
if not app.debug:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)

# 加载视图
from wxcloudrun import views

# 确保每次请求完成后正确关闭数据库会话
@app.teardown_appcontext
def shutdown_session(exception=None):
    if exception:
        db.session.rollback()
    db.session.remove()