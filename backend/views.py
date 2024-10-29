# wxcloudrun/views.py

from flask import Blueprint, render_template, request, current_app
import urllib
from apiflask import APIBlueprint, Schema
from apiflask.fields import String
from . import db

# 创建 Blueprint
# main_bp = Blueprint('main', __name__, template_folder='templates')
main_bp = APIBlueprint('main', __name__, url_prefix='/api')

# 定义视图路由
@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/routes')
def list_routes():
    output = []
    for rule in current_app.url_map.iter_rules():
        methods = ','.join(sorted(rule.methods))
        line = urllib.parse.unquote(f"{rule.endpoint:30s} {methods:20s} {rule}")
        output.append(line)
    return '<br>'.join(output)