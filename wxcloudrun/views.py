# wxcloudrun/views.py

from flask import Blueprint, render_template, request
from flask_restful import Resource, reqparse
from flask_jwt_extended import (
    jwt_required, get_jwt_identity
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

import os
import sys
import logging
import tempfile
from datetime import datetime

import openai
from qcloud_cos import CosConfig, CosS3Client

from . import db, api
from .model import User, TranslationRecord
from .response import (
    make_succ_empty_response,
    make_succ_response,
    make_err_response
)
from .config import Config

# 配置日志
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger()

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """
    检查上传的文件是否具有允许的扩展名。
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 初始化 COS 客户端
def get_cos_client():
    """
    使用配置初始化并返回 COS 客户端。
    """
    config = CosConfig(
        Region=Config.COS_REGION,
        SecretId=Config.COS_SECRET_ID,
        SecretKey=Config.COS_SECRET_KEY,
        Token=Config.COS_TOKEN,       # 如果使用临时密钥
        Scheme=Config.COS_SCHEME      # 'https' 或 'http'
    )
    client = CosS3Client(config)
    return client

# 创建 Blueprint
main_bp = Blueprint('main', __name__, template_folder='templates')

# 定义视图路由
@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/routes')
def list_routes():
    import urllib
    output = []
    for rule in current_app.url_map.iter_rules():
        methods = ','.join(rule.methods)
        line = urllib.parse.unquote(f"{rule.endpoint:30s} {methods:20s} {rule}")
        output.append(line)
    return '<br>'.join(output)

# 用户注册资源
class UserRegister(Resource):
    def post(self):
        data = register_parser.parse_args()
        username = data['username']
        password = data['password']

        if User.query.filter_by(username=username).first():
            return make_err_response('用户已存在'), 400

        hashed_password = generate_password_hash(password)
        user = User(username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()

        return make_succ_response('用户创建成功'), 201

# 用户登录资源
class UserLogin(Resource):
    def post(self):
        data = login_parser.parse_args()
        username = data['username']
        password = data['password']

        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password, password):
            return make_err_response('无效的凭证'), 401

        access_token = create_access_token(identity=user.id)
        return make_succ_response({'access_token': access_token}), 200

# 图片上传和翻译资源
class ImageUpload(Resource):
    @jwt_required()
    def post(self):
        if 'image' not in request.files:
            return make_err_response('未提供图片文件'), 400

        file = request.files['image']
        if file.filename == '':
            return make_err_response('未选择文件'), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            cos_client = get_cos_client()
            cos_path = f"uploads/{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"  # 唯一路径

            # 使用临时文件保存上传的图片
            try:
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    file.save(temp_file)
                    temp_file_path = temp_file.name

                # 使用推荐的 upload_file 方法上传到 COS
                response = cos_client.upload_file(
                    Bucket=Config.COS_BUCKET,
                    LocalFilePath=temp_file_path,
                    Key=cos_path,
                    PartSize=5,           # PartSize 以 MB 为单位，根据需要调整（建议 1-5MB）
                    MAXThread=10,         # 分段上传的线程数
                    EnableMD5=True        # 启用 MD5 校验
                )
                logger.info(f"文件已上传到 COS: {cos_path}")
                # 上传后删除临时文件
                os.remove(temp_file_path)

                file_url = f"https://{Config.COS_BUCKET}.cos.{Config.COS_REGION}.myqcloud.com/{cos_path}"
                file_id = response.get('ETag', '')  # 如果需要，可以使用 ETag 作为文件 ID
            except Exception as e:
                logger.error(f"上传到 COS 失败: {str(e)}")
                return make_err_response('上传到 COS 失败', error=str(e)), 500

            # 创建 OpenAI 消息负载
            messages = [
                {"role": "system", "content": "你是一个将日语菜单图片内容翻译成中文的助手。"},
                {"role": "user", "content": [
                    {"type": "text", "text": "请将以下日语菜单图片内容翻译成中文："},
                    {"type": "image_url", "image_url": file_url}  # 使用 OpenAI 的 HTTPS URL
                ]}
            ]

            # 使用 GPT-4 API 进行翻译
            try:
                openai.api_key = Config.OPENAI_API_KEY
                openai_model = Config.OPENAI_MODEL  # 确保已设置，例如 "gpt-4"
                chat_response = openai.ChatCompletion.create(
                    model=openai_model,
                    messages=messages,
                    temperature=0.0,
                )
                chinese_translation = chat_response.choices[0].message.content.strip()
                logger.info("翻译成功")
            except Exception as e:
                logger.error(f"翻译失败: {str(e)}")
                return make_err_response('翻译失败', error=str(e)), 500

            # 将翻译记录保存到数据库
            try:
                user_id = get_jwt_identity()
                record = TranslationRecord(
                    cos_file_id=cos_path,
                    chinese_translation=chinese_translation,
                    user_id=user_id
                )
                db.session.add(record)
                db.session.commit()
                logger.info(f"翻译记录已保存: {record.id}")
            except Exception as e:
                logger.error(f"保存翻译记录失败: {str(e)}")
                return make_err_response('保存翻译记录失败', error=str(e)), 500

            return make_succ_response({
                'record_id': record.id,
                'chinese_translation': chinese_translation
            }), 201
        else:
            return make_err_response('不支持的文件类型'), 400

# 翻译记录检索资源
class TranslationRecordResource(Resource):
    @jwt_required()
    def get(self, record_id):
        user_id = get_jwt_identity()
        record = TranslationRecord.query.filter_by(id=record_id, user_id=user_id).first()

        if not record:
            return make_err_response('记录未找到'), 404

        return make_succ_response({
            'id': record.id,
            'cos_file_id': record.cos_file_id,
            'chinese_translation': record.chinese_translation,
            'created_at': record.created_at.isoformat()
        }), 200

# 翻译记录列表资源
class TranslationRecordsListResource(Resource):
    @jwt_required()
    def get(self):
        user_id = get_jwt_identity()
        records = TranslationRecord.query.filter_by(user_id=user_id).order_by(TranslationRecord.created_at.desc()).all()
        records_data = [{
            'id': record.id,
            'cos_file_id': record.cos_file_id,
            'chinese_translation': record.chinese_translation,
            'created_at': record.created_at.isoformat()
        } for record in records]

        return make_succ_response({'records': records_data}), 200

# 用户登出资源（可选，因为 JWT 是无状态的）
class UserLogout(Resource):
    @jwt_required()
    def post(self):
        # 要实现令牌撤销，您需要设置一个令牌黑名单
        # 这是可选的，需要额外的设置
        return make_succ_response('登出成功'), 200

# 注册 API 资源和端点
api.add_resource(UserRegister, '/api/register')
api.add_resource(UserLogin, '/api/login')
api.add_resource(ImageUpload, '/api/upload_image')
api.add_resource(TranslationRecordResource, '/api/translation/<int:record_id>')
api.add_resource(TranslationRecordsListResource, '/api/records')
api.add_resource(UserLogout, '/api/logout')  # 可选