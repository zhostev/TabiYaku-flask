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

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger()

# Initialize COS client
def get_cos_client():
    """
    Initialize and return a COS client using the configurations.
    """
    config = CosConfig(
        Region=Config.COS_REGION,
        SecretId=Config.COS_SECRET_ID,
        SecretKey=Config.COS_SECRET_KEY,
        Token=Config.COS_TOKEN,       # Optional, if using temporary credentials
        Scheme=Config.COS_SCHEME      # 'https' or 'http'
    )
    client = CosS3Client(config)
    return client

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """
    Check if the uploaded file has an allowed extension.
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Request parsers
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
            cos_client = get_cos_client()
            cos_path = f"test/{filename}"  # Modify directory structure as needed

            # Use a temporary file to store the uploaded image
            try:
                with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                    file.save(temp_file)
                    temp_file_path = temp_file.name

                # Upload file to COS using the recommended upload_file method
                response = cos_client.upload_file(
                    Bucket=Config.COS_BUCKET,
                    LocalFilePath=temp_file_path,
                    Key=cos_path,
                    PartSize=5,           # Part size in MB (1-5MB recommended)
                    MAXThread=10,         # Number of threads
                    EnableMD5=True        # Enable MD5 checksum
                )
                logger.info(f"File uploaded to COS: {cos_path}")
                # Delete the temporary file after upload
                os.remove(temp_file_path)

                file_url = f"https://{Config.COS_BUCKET}.cos.{Config.COS_REGION}.myqcloud.com/{cos_path}"
                file_id = response.get('ETag', '')  # Use ETag as file ID if needed
            except Exception as e:
                logger.error(f"Failed to upload to COS: {str(e)}")
                return {'message': 'Failed to upload to COS', 'error': str(e)}, 500

            # Create OpenAI messages payload
            messages = [
                {"role": "system", "content": "你是一个将日语菜单图片内容翻译成中文的助手。"},
                {"role": "user", "content": [
                    {"type": "text", "text": "请将以下日语菜单图片内容翻译成中文："},
                    {"type": "image_url", "image_url": file_url}  # Use the HTTPS URL for OpenAI
                ]}
            ]

            # Use GPT-4 API for translation
            try:
                openai.api_key = Config.OPENAI_API_KEY
                openai_model = Config.OPENAI_MODEL  # Ensure this is set, e.g., "gpt-4"
                chat_response = openai.ChatCompletion.create(
                    model=openai_model,
                    messages=messages,
                    temperature=0.0,
                )
                chinese_translation = chat_response.choices[0].message.content.strip()
                logger.info("Translation successful")
            except Exception as e:
                logger.error(f"Translation failed: {str(e)}")
                return {'message': 'Translation failed', 'error': str(e)}, 500

            # Save translation record to the database
            try:
                user_id = get_jwt_identity()
                record = TranslationRecord(
                    cos_file_id=cos_path,
                    chinese_translation=chinese_translation,
                    user_id=user_id
                )
                db.session.add(record)
                db.session.commit()
                logger.info(f"Translation record saved: {record.id}")
            except Exception as e:
                logger.error(f"Failed to save translation record: {str(e)}")
                return {'message': 'Failed to save translation record', 'error': str(e)}, 500

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
            'cos_file_id': record.cos_file_id,
            'chinese_translation': record.chinese_translation,
            'created_at': record.created_at.isoformat()
        }, 200