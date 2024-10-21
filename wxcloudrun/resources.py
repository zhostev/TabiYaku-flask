# wxcloudrun/resources.py

from flask_restful import Resource, reqparse
from flask import request
from werkzeug.utils import secure_filename
from . import db
from .model import User, TranslationRecord
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import os
import openai
import base64
from werkzeug.security import generate_password_hash, check_password_hash
from .config import Config
from qcloud_cos import CosConfig, CosS3Client
from urllib.parse import urlparse
import logging
import sys
import tempfile
from datetime import datetime
from openai import OpenAI  # 新增导入


# 配置日志
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# 设置 OpenAI 库的日志记录级别为 DEBUG（可选）
openai_logger = logging.getLogger("openai")
openai_logger.setLevel(logging.DEBUG)

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

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """
    检查上传的文件是否具有允许的扩展名。
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 请求解析器
register_parser = reqparse.RequestParser()
register_parser.add_argument('username', type=str, required=True, help='用户名是必需的')
register_parser.add_argument('password', type=str, required=True, help='密码是必需的')

login_parser = reqparse.RequestParser()
login_parser.add_argument('username', type=str, required=True, help='用户名是必需的')
login_parser.add_argument('password', type=str, required=True, help='密码是必需的')

# 初始化 OpenAI 客户端
client = OpenAI(api_key=Config.OPENAI_API_KEY)
client.api_base = Config.OPENAI_API_BASE

class UserRegister(Resource):
    def post(self):
        try:
            data = register_parser.parse_args()
            username = data['username']
            password = data['password']

            if User.query.filter_by(username=username).first():
                logger.info(f"注册失败: 用户 '{username}' 已存在")
                return {'message': '用户已存在'}, 400

            hashed_password = generate_password_hash(password)
            user = User(username=username, password=hashed_password)
            db.session.add(user)
            db.session.commit()

            logger.info(f"用户 '{username}' 注册成功")
            return {'message': '用户创建成功'}, 201
        except Exception as e:
            logger.error(f"注册过程中出现错误: {str(e)}")
            return {'message': '注册过程中出现错误', 'error': str(e)}, 500

class UserLogin(Resource):
    def post(self):
        try:
            data = login_parser.parse_args()
            username = data['username']
            password = data['password']

            user = User.query.filter_by(username=username).first()
            if not user or not check_password_hash(user.password, password):
                logger.info(f"登录失败: 无效的凭证 for user '{username}'")
                return {'message': '无效的凭证'}, 401

            access_token = create_access_token(identity=user.id)
            logger.info(f"用户 '{username}' 登录成功")
            return {'access_token': access_token}, 200
        except Exception as e:
            logger.error(f"登录过程中出现错误: {str(e)}")
            return {'message': '登录过程中出现错误', 'error': str(e)}, 500

class ImageUpload(Resource):
    @jwt_required()
    def post(self):
        try:
            logger.info("开始处理图片上传请求")
            if 'image' not in request.files:
                logger.warning("上传失败: 未提供图片文件")
                return {'message': '未提供图片文件'}, 400
            file = request.files['image']
            if file.filename == '':
                logger.warning("上传失败: 未选择文件")
                return {'message': '未选择文件'}, 400
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                cos_client = get_cos_client()
                timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
                cos_path = f"uploads/{timestamp}_{filename}"  # 唯一路径

                # 使用临时文件保存上传的图片
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    file.save(temp_file)
                    temp_file_path = temp_file.name

                try:
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
                except Exception as e:
                    logger.error(f"上传到 COS 失败: {str(e)}")
                    os.remove(temp_file_path)  # 上传失败后删除临时文件
                    return {'message': '上传到 COS 失败', 'error': str(e)}, 500

                # 上传后删除临时文件
                os.remove(temp_file_path)

                file_url = f"https://{Config.COS_BUCKET}.cos.{Config.COS_REGION}.myqcloud.com/{cos_path}"
                logger.info(f"生成的文件 URL: {file_url}")

                # 创建 OpenAI 消息负载，包括文本和图像 URL
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "请将以下日语菜单图片内容翻译成中文："},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": file_url
                                }
                            }
                        ]
                    }
                ]


                # 记录即将访问的 OpenAI API 端点
                openai_api_url = f"{Config.OPENAI_API_BASE}/chat/completions"
                logger.info(f"即将访问 OpenAI API 端点: {openai_api_url} with model {Config.OPENAI_MODEL}")
                
                # 使用 GPT-4o API 进行翻译
                try:
                    response = client.chat.completions.create(
                        model=Config.OPENAI_MODEL,  # 确保 Config.OPENAI_MODEL 设置为 "gpt-4o"
                        messages=messages,
                        max_tokens=300,
                        temperature=0.0,
                        request_timeout=10  # 设置超时时间为 10 秒

                    )
                    assistant_message = response.choices[0].message['content'].strip()
                    chinese_translation = assistant_message
                    logger.info("翻译成功")
                except Exception as e:
                    # 捕获其他可能的异常
                    logger.error(f"未知错误: {str(e)}")
                    return {'message': '未知错误', 'error': str(e)}, 500

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
                    return {'message': '保存翻译记录失败', 'error': str(e)}, 500

                return {
                    'record_id': record.id,
                    'chinese_translation': chinese_translation
                }, 201
            else:
                logger.warning("上传失败: 不支持的文件类型")
                return {'message': '不支持的文件类型'}, 400
        except Exception as e:
            logger.error(f"处理图片上传时出现错误: {str(e)}")
            return {'message': '处理图片上传时出现错误', 'error': str(e)}, 500

class TranslationRecordResource(Resource):
    @jwt_required()
    def get(self, record_id):
        try:
            user_id = get_jwt_identity()
            record = TranslationRecord.query.filter_by(id=record_id, user_id=user_id).first()
            if not record:
                logger.warning(f"记录未找到: ID {record_id} for user {user_id}")
                return {'message': '记录未找到'}, 404
            return {
                'id': record.id,
                'cos_file_id': record.cos_file_id,
                'chinese_translation': record.chinese_translation,
                'created_at': record.created_at.isoformat()
            }, 200
        except Exception as e:
            logger.error(f"获取记录时出现错误: {str(e)}")
            return {'message': '获取记录时出现错误', 'error': str(e)}, 500

class TranslationRecordsListResource(Resource):
    @jwt_required()
    def get(self):
        try:
            user_id = get_jwt_identity()
            records = TranslationRecord.query.filter_by(user_id=user_id).order_by(TranslationRecord.created_at.desc()).all()
            records_data = [{
                'id': record.id,
                'cos_file_id': record.cos_file_id,
                'chinese_translation': record.chinese_translation,
                'created_at': record.created_at.isoformat()
            } for record in records]

            logger.info(f"用户 {user_id} 请求获取所有翻译记录")
            return {'records': records_data}, 200
        except Exception as e:
            logger.error(f"获取所有翻译记录时出现错误: {str(e)}")
            return {'message': '获取记录时出现错误', 'error': str(e)}, 500

class UserLogout(Resource):
    @jwt_required()
    def post(self):
        try:
            # 要实现令牌撤销，您需要设置一个令牌黑名单
            # 这是可选的，需要额外的设置
            logger.info("用户登出请求")
            return {'message': '登出成功'}, 200
        except Exception as e:
            logger.error(f"登出时出现错误: {str(e)}")
            return {'message': '登出时出现错误', 'error': str(e)}, 500