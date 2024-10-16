# views.py

# -*- coding=utf-8 -*-
import os
import sys
import logging
import tempfile
from datetime import datetime

from flask import Flask, render_template, request
from flask_restful import Api, Resource, reqparse
from flask_jwt_extended import (
    JWTManager, create_access_token,
    jwt_required, get_jwt_identity
)
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

import openai
from qcloud_cos import CosConfig, CosS3Client

# Import custom modules
from wxcloudrun.dao import (
    delete_counterbyid,
    query_counterbyid,
    insert_counter,
    update_counterbyid
)
from wxcloudrun.model import Counters, User, TranslationRecord
from wxcloudrun.response import (
    make_succ_empty_response,
    make_succ_response,
    make_err_response
)
from wxcloudrun.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger()

# Initialize Flask app
app = Flask(__name__, template_folder='templates')

# Enable CORS (adjust origins as needed)
CORS(app)

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = Config.SQLALCHEMY_DATABASE_URI  # e.g., 'sqlite:///your_database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = Config.JWT_SECRET_KEY  # Replace with a secure key
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB upload limit

# Initialize extensions
db = SQLAlchemy(app)
api = Api(app)
jwt = JWTManager(app)

# Allowed file extensions for image upload
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    """
    Check if the uploaded file has an allowed extension.
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Initialize COS client
def get_cos_client():
    """
    Initialize and return a COS client using the configurations.
    """
    config = CosConfig(
        Region=Config.COS_REGION,
        SecretId=Config.COS_SECRET_ID,
        SecretKey=Config.COS_SECRET_KEY,
        Token=Config.COS_TOKEN,       # Assuming you might use temporary keys
        Scheme=Config.COS_SCHEME      # 'https' or 'http'
    )
    client = CosS3Client(config)
    return client


# Flask-RESTful Request Parsers
register_parser = reqparse.RequestParser()
register_parser.add_argument('username', type=str, required=True, help='Username is required')
register_parser.add_argument('password', type=str, required=True, help='Password is required')

login_parser = reqparse.RequestParser()
login_parser.add_argument('username', type=str, required=True, help='Username is required')
login_parser.add_argument('password', type=str, required=True, help='Password is required')


# User Registration Resource
class UserRegister(Resource):
    def post(self):
        data = register_parser.parse_args()
        username = data['username']
        password = data['password']

        if User.query.filter_by(username=username).first():
            return make_err_response('User already exists'), 400

        hashed_password = generate_password_hash(password)
        user = User(username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()

        return make_succ_response('User created successfully'), 201


# User Login Resource
class UserLogin(Resource):
    def post(self):
        data = login_parser.parse_args()
        username = data['username']
        password = data['password']

        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password, password):
            return make_err_response('Invalid credentials'), 401

        access_token = create_access_token(identity=user.id)
        return make_succ_response({'access_token': access_token}), 200


# Image Upload and Translation Resource
class ImageUpload(Resource):
    @jwt_required()
    def post(self):
        if 'image' not in request.files:
            return make_err_response('No image file provided'), 400

        file = request.files['image']
        if file.filename == '':
            return make_err_response('No selected file'), 400

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            cos_client = get_cos_client()
            cos_path = f"uploads/{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"  # Unique path

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
                    PartSize=5,           # PartSize in MB, adjust as needed (1-5MB recommended)
                    MAXThread=10,         # Number of threads for multipart upload
                    EnableMD5=True        # Enable MD5 checksum for verification
                )
                logger.info(f"File uploaded to COS: {cos_path}")
                # Delete the temporary file after upload
                os.remove(temp_file_path)

                file_url = f"https://{Config.COS_BUCKET}.cos.{Config.COS_REGION}.myqcloud.com/{cos_path}"
                file_id = response.get('ETag', '')  # Use ETag as file ID if needed
            except Exception as e:
                logger.error(f"Failed to upload to COS: {str(e)}")
                return make_err_response('Failed to upload to COS', error=str(e)), 500

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
                return make_err_response('Translation failed', error=str(e)), 500

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
                return make_err_response('Failed to save translation record', error=str(e)), 500

            return make_succ_response({
                'record_id': record.id,
                'chinese_translation': chinese_translation
            }), 201
        else:
            return make_err_response('Unsupported file type'), 400


# Translation Record Retrieval Resource
class TranslationRecordResource(Resource):
    @jwt_required()
    def get(self, record_id):
        user_id = get_jwt_identity()
        record = TranslationRecord.query.filter_by(id=record_id, user_id=user_id).first()

        if not record:
            return make_err_response('Record not found'), 404

        return make_succ_response({
            'id': record.id,
            'cos_file_id': record.cos_file_id,
            'chinese_translation': record.chinese_translation,
            'created_at': record.created_at.isoformat()
        }), 200


# Translation Records List Resource
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


# User Logout Resource (optional, since JWTs are stateless)
class UserLogout(Resource):
    @jwt_required()
    def post(self):
        # To implement token revocation, you need to set up a token blacklist
        # This is optional and requires additional setup
        return make_succ_response('Logout successful'), 200


# Register API Resources with Endpoints
api.add_resource(UserRegister, '/api/register')
api.add_resource(UserLogin, '/api/login')
api.add_resource(ImageUpload, '/api/upload')
api.add_resource(TranslationRecordResource, '/api/translation/<int:record_id>')
api.add_resource(TranslationRecordsListResource, '/api/records')
api.add_resource(UserLogout, '/api/logout')  # Optional


# Existing Routes

@app.route('/')
def index():
    """
    Serve the index HTML page.
    """
    return render_template('index.html')


@app.route('/api/count', methods=['POST'])
def count():
    """
    Handle count increment or reset actions.
    """
    # 获取请求体参数
    params = request.get_json()

    # 检查action参数
    if not params or 'action' not in params:
        return make_err_response('缺少action参数'), 400

    # 按照不同的action的值，进行不同的操作
    action = params['action']

    # 执行自增操作
    if action == 'inc':
        counter = query_counterbyid(1)
        if counter is None:
            counter = Counters(
                id=1,
                count=1,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            insert_counter(counter)
        else:
            counter.count += 1
            counter.updated_at = datetime.now()
            update_counterbyid(counter)
        return make_succ_response({'data': counter.count}), 200

    # 执行清0操作
    elif action == 'clear':
        delete_counterbyid(1)
        return make_succ_empty_response(), 200

    # action参数错误
    else:
        return make_err_response('action参数错误'), 400


@app.route('/api/count', methods=['GET'])
def get_count():
    """
    Retrieve the current count value.
    """
    counter = Counters.query.filter(Counters.id == 1).first()
    current_count = 0 if counter is None else counter.count
    return make_succ_response({'data': current_count}), 200


# Run the Flask app
if __name__ == '__main__':
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)