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

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 请求参数解析器
register_parser = reqparse.RequestParser()
register_parser.add_argument('username', type=str, required=True, help='Username is required')
register_parser.add_argument('password', type=str, required=True, help='Password is required')

login_parser = reqparse.RequestParser()
login_parser.add_argument('username', type=str, required=True, help='Username is required')
login_parser.add_argument('password', type=str, required=True, help='Password is required')

class UserRegister(Resource):
    def post(self):
        data = register_parser.parse_args()
        username = data['username']
        password = data['password']
        if User.query.filter_by(username=username).first():
            return {'message': 'User already exists'}, 400
        hashed_password = generate_password_hash(password)
        user = User(username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        return {'message': 'User created successfully'}, 201

class UserLogin(Resource):
    def post(self):
        data = login_parser.parse_args()
        username = data['username']
        password = data['password']
        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password, password):
            return {'message': 'Invalid credentials'}, 401
        access_token = create_access_token(identity=user.id)
        return {'access_token': access_token}, 200

class ImageUpload(Resource):
    @jwt_required()
    def post(self):
        if 'image' not in request.files:
            return {'message': 'No image file provided'}, 400
        file = request.files['image']
        if file.filename == '':
            return {'message': 'No selected file'}, 400
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(Config.UPLOAD_FOLDER, filename)
            os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
            file.save(save_path)
            
            # 读取图片文件并编码为 base64
            try:
                with open(save_path, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            except Exception as e:
                return {'message': 'Failed to read image file', 'error': str(e)}, 500
                
            # 创建 GPT-4 的 messages payload
            messages = [
                {"role": "system", "content": "你是一个将日语菜单图片内容翻译成中文的助手。"},
                {"role": "user", "content": [
                    {"type": "text", "text": "请将以下日语菜单图片内容翻译成中文："},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/{filename.rsplit('.', 1)[1].lower()};base64,{base64_image}"
                    }}
                ]}
            ]
            
            # 使用 GPT-4 API 进行翻译
            try:
                openai.api_key = Config.OPENAI_API_KEY
                response = openai.ChatCompletion.create(
                    model=Config.OPENAI_MODEL,
                    messages=messages,
                    temperature=0.0,
                )
                chinese_translation = response.choices[0].message.content.strip()
            except Exception as e:
                return {'message': 'Translation failed', 'error': str(e)}, 500
            
            # 保存翻译记录
            user_id = get_jwt_identity()
            record = TranslationRecord(
                image_path=save_path,
                chinese_translation=chinese_translation,
                user_id=user_id
            )
            db.session.add(record)
            db.session.commit()
            
            return {
                'record_id': record.id,
                'chinese_translation': chinese_translation
            }, 201
        else:
            return {'message': 'Unsupported file type'}, 400

class TranslationRecordResource(Resource):
    @jwt_required()
    def get(self, record_id):
        user_id = get_jwt_identity()
        record = TranslationRecord.query.filter_by(id=record_id, user_id=user_id).first()
        if not record:
            return {'message': 'Record not found'}, 404
        return {
            'id': record.id,
            'image_path': record.image_path,
            'chinese_translation': record.chinese_translation,
            'created_at': record.created_at.isoformat()
        }, 200