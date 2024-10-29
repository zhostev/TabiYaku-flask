# wxcloudrun/resources.py

from apiflask import APIBlueprint, abort, Schema, fields
from apiflask.validators import Length
from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity,
    create_access_token
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from .model import User, TranslationRecord
from .config import Config
from qcloud_cos import CosConfig, CosS3Client
import os
import tempfile
import logging
import sys
from datetime import datetime
import openai
import traceback  # 用于详细的错误日志

# Initialize logger
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)
logger.info("Resources module loaded successfully")

# Initialize OpenAI client
openai.api_key = Config.OPENAI_API_KEY
openai.api_base = Config.OPENAI_API_BASE

# Initialize COS client function
def get_cos_client():
    """
    Initialize and return the COS client using the configuration.
    """
    config = CosConfig(
        Region=Config.COS_REGION,
        SecretId=Config.COS_SECRET_ID,
        SecretKey=Config.COS_SECRET_KEY,
        Token=Config.COS_TOKEN,       # If using temporary credentials
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

# Define APIBlueprint
main_bp = APIBlueprint('main', __name__, url_prefix='/api')

# Schemas for request and response validation
class RegisterSchema(Schema):
    username = fields.String(required=True, validate=Length(min=1))
    password = fields.String(required=True, validate=Length(min=6))

class LoginSchema(Schema):
    username = fields.String(required=True, validate=Length(min=1))
    password = fields.String(required=True, validate=Length(min=6))

class UserSchema(Schema):
    id = fields.Integer()
    username = fields.String()

class TokenSchema(Schema):
    access_token = fields.String()

class UploadResponseSchema(Schema):
    record_id = fields.Integer()
    chinese_translation = fields.String()

class TranslationRecordSchema(Schema):
    id = fields.Integer()
    cos_file_id = fields.String()
    chinese_translation = fields.String()
    created_at = fields.DateTime()

class TranslationRecordsListSchema(Schema):
    records = fields.List(fields.Nested(TranslationRecordSchema))

class UploadSchema(Schema):
    image = fields.File(required=True, description="Image file to upload")

# Routes

@main_bp.post('/register')
@main_bp.input(RegisterSchema)
@main_bp.output(UserSchema, status_code=201)
def register(data):
    """
    Register a new user.
    """
    try:
        username = data['username']
        password = data['password']

        if User.query.filter_by(username=username).first():
            logger.info(f"Registration failed: User '{username}' already exists")
            abort(400, message='User already exists')

        hashed_password = generate_password_hash(password)
        user = User(username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()

        logger.info(f"User '{username}' registered successfully")
        return {'id': user.id, 'username': user.username}, 201
    except Exception as e:
        logger.error(f"Error during registration: {str(e)}")
        logger.error(traceback.format_exc())  # 记录完整的堆栈跟踪
        abort(500, message='Error during registration')

@main_bp.post('/login')
@main_bp.input(LoginSchema)
@main_bp.output(TokenSchema)
def login(data):
    """
    User login to obtain JWT.
    """
    try:
        username = data['username']
        password = data['password']

        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password, password):
            logger.info(f"Login failed: Invalid credentials for user '{username}'")
            abort(401, message='Invalid credentials')

        access_token = create_access_token(identity=user.id)
        logger.info(f"User '{username}' logged in successfully")
        return {'access_token': access_token}, 200
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        logger.error(traceback.format_exc())  # 记录完整的堆栈跟踪
        # 仅开发环境下返回详细错误信息
        abort(500, message=f'Error during login: {str(e)}')

@main_bp.post('/upload')
@jwt_required()
@main_bp.input(UploadSchema, location='files')
@main_bp.output(UploadResponseSchema, status_code=201)
def upload_image(data):
    """
    Upload an image for translation.
    """
    try:
        logger.info("Processing image upload request")

        if 'image' not in data:
            logger.warning("Upload failed: No image file provided")
            abort(400, message='No image file provided')

        file = data['image']
        if not file.filename:
            logger.warning("Upload failed: No file selected")
            abort(400, message='No file selected')

        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            cos_client = get_cos_client()
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            cos_path = f"uploads/{timestamp}_{filename}"  # Unique path

            # Save the uploaded image to a temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                file.save(temp_file)
                temp_file_path = temp_file.name

            try:
                # Upload to COS
                response = cos_client.upload_file(
                    Bucket=Config.COS_BUCKET,
                    LocalFilePath=temp_file_path,
                    Key=cos_path,
                    PartSize=5,           # PartSize in MB, adjust as needed
                    MAXThread=10,         # Number of threads for multipart upload
                    EnableMD5=True        # Enable MD5 check
                )
                logger.info(f"File uploaded to COS: {cos_path}")
            except Exception as e:
                logger.error(f"Error uploading to COS: {str(e)}")
                os.remove(temp_file_path)  # Remove temp file on failure
                abort(500, message='Error uploading to COS')

            # Remove the temporary file after upload
            os.remove(temp_file_path)

            file_url = f"https://{Config.COS_BUCKET}.cos.{Config.COS_REGION}.myqcloud.com/{cos_path}"
            logger.info(f"Generated file URL: {file_url}")

            # Create OpenAI message payload
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

            # Log OpenAI API endpoint access
            openai_api_url = f"{Config.OPENAI_API_BASE}/chat/completions"
            logger.info(f"Accessing OpenAI API endpoint: {openai_api_url} with model {Config.OPENAI_MODEL}")

            # Use GPT-4 API for translation
            try:
                response = openai.ChatCompletion.create(
                    model=Config.OPENAI_MODEL,  # Ensure Config.OPENAI_MODEL is set to "gpt-4"
                    messages=messages,
                    max_tokens=300,
                    temperature=0.0,
                    request_timeout=10  # Set timeout to 10 seconds
                )
                assistant_message = response.choices[0].message['content'].strip()
                chinese_translation = assistant_message
                logger.info("Translation successful")
            except Exception as e:
                logger.error(f"OpenAI API error: {str(e)}")
                logger.error(traceback.format_exc())  # 记录完整的堆栈跟踪
                abort(500, message='Translation service error')

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
                logger.error(f"Error saving translation record: {str(e)}")
                logger.error(traceback.format_exc())  # 记录完整的堆栈跟踪
                abort(500, message='Error saving translation record')

            return {
                'record_id': record.id,
                'chinese_translation': chinese_translation
            }, 201
        else:
            logger.warning("Upload failed: Unsupported file type")
            abort(400, message='Unsupported file type')
    except Exception as e:
        logger.error(f"Error processing image upload: {str(e)}")
        logger.error(traceback.format_exc())  # 记录完整的堆栈跟踪
        abort(500, message='Error processing image upload')

@main_bp.get('/records/<int:record_id>')
@jwt_required()
@main_bp.output(TranslationRecordSchema)
def get_record(record_id):
    """
    Retrieve a specific translation record.
    """
    try:
        user_id = get_jwt_identity()
        record = TranslationRecord.query.filter_by(id=record_id, user_id=user_id).first()
        if not record:
            logger.warning(f"Record not found: ID {record_id} for user {user_id}")
            abort(404, message='Record not found')

        return {
            'id': record.id,
            'cos_file_id': record.cos_file_id,
            'chinese_translation': record.chinese_translation,
            'created_at': record.created_at.isoformat()
        }, 200
    except Exception as e:
        logger.error(f"Error retrieving record: {str(e)}")
        logger.error(traceback.format_exc())  # 记录完整的堆栈跟踪
        abort(500, message='Error retrieving record')

@main_bp.get('/records')
@jwt_required()
@main_bp.output(TranslationRecordsListSchema)
def list_records():
    """
    Retrieve all translation records for the authenticated user.
    """
    try:
        user_id = get_jwt_identity()
        records = TranslationRecord.query.filter_by(user_id=user_id).order_by(TranslationRecord.created_at.desc()).all()
        records_data = [{
            'id': record.id,
            'cos_file_id': record.cos_file_id,
            'chinese_translation': record.chinese_translation,
            'created_at': record.created_at.isoformat()
        } for record in records]

        logger.info(f"User {user_id} requested all translation records")
        return {'records': records_data}, 200
    except Exception as e:
        logger.error(f"Error retrieving all records: {str(e)}")
        logger.error(traceback.format_exc())  # 记录完整的堆栈跟踪
        abort(500, message='Error retrieving records')

@main_bp.post('/logout')
@jwt_required()
def logout():
    """
    User logout (token revocation would require additional setup).
    """
    try:
        # Implement token revocation logic here if using a token blacklist
        logger.info("User logout requested")
        return {'message': 'Logout successful'}, 200
    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        logger.error(traceback.format_exc())  # 记录完整的堆栈跟踪
        abort(500, message='Error during logout')