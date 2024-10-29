# app/__init__.py

import os
from flask import Flask, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_cors import CORS
from flask_restx import Api
from dotenv import load_dotenv
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import LoginManager, current_user

# 加载环境变量
load_dotenv()

# 初始化扩展
db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()
api = Api(
    title='TabiYaku API',
    version='1.0',
    description='API documentation for TabiYaku',
)
login_manager = LoginManager()
login_manager.login_view = 'auth.login'  # 指定登录视图

# 自定义 AdminIndexView 以控制访问权限
class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            return redirect(url_for('auth.login', next=request.url))
        return super(MyAdminIndexView, self).index()

    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, 'is_admin', False)

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('auth.login', next=request.url))

# 自定义 ModelView 以控制访问权限
class MyModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, 'is_admin', False)

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('auth.login', next=request.url))

def create_app():
    app = Flask(__name__)
    app.config.from_object('config')  # 使用配置类

    # 初始化扩展
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    api.init_app(app)
    login_manager.init_app(app)

    # 导入所有模型以确保 Alembic 能检测到它们
    from app.models import User, Translation  # 添加所有模型

    # 注册 Flask-RESTX 命名空间
    from app.routes import auth_ns, translate_ns, users_ns
    api.add_namespace(auth_ns, path='/api/auth')
    api.add_namespace(translate_ns, path='/api/translate')
    api.add_namespace(users_ns, path='/api/users')  # 注册 users 命名空间

    # 注册传统的 Flask 视图 Blueprint
    from app.views.auth import auth_bp
    app.register_blueprint(auth_bp)

    # 初始化 Flask-Admin，使用自定义 AdminIndexView
    admin = Admin(app, name='管理后台', template_mode='bootstrap3', index_view=MyAdminIndexView())
    admin.add_view(MyModelView(User, db.session))  # 使用自定义 MyModelView

    # 创建上传文件夹，如果不存在则创建，并处理权限错误
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    except PermissionError:
        app.logger.error(f"Permission denied while creating directory: {app.config['UPLOAD_FOLDER']}")
        raise

    return app

# Flask-Login 用户加载回调
@login_manager.user_loader
def load_user(user_id):
    from .models import User
    return User.query.get(int(user_id))