from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from flask import redirect, url_for, request
from .models import db, User

class AdminModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('auth.login', next=request.url))

def init_admin(app):
    admin = Admin(app, name='管理后台', template_mode='bootstrap3')
    admin.add_view(AdminModelView(User, db.session))
    # 你可以在这里添加更多的模型视图