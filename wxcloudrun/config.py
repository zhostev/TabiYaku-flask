# config.py

import os

class Config:
    # 基础配置
    DEBUG = os.environ.get('FLASK_ENV') == 'development'
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your_secret_key')
    
    # 数据库配置
    MYSQL_USERNAME = os.environ.get('MYSQL_USERNAME', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'password')
    MYSQL_ADDRESS = os.environ.get('MYSQL_ADDRESS', 'localhost:3306')
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{MYSQL_USERNAME}:{MYSQL_PASSWORD}@{MYSQL_ADDRESS}/flask_demo"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT 配置
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your_jwt_secret_key')  # 添加这行以解决错误

    # OpenAI 配置
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', 'your_openai_api_key')
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4')
    OPENAI_API_BASE = os.environ.get('OPENAI_API_BASE', 'https://lsapi.zeabur.app/v1')  # 新增 OpenAI API 基础 URL
    
    # 上传文件夹
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/app/uploads/')
    
    # 腾讯云COS配置
    COS_BUCKET = os.environ.get('COS_BUCKET')
    COS_REGION = os.environ.get('COS_REGION')
    COS_SECRET_ID = os.environ.get('COS_SECRET_ID')      # 腾讯云COS的Secret ID
    COS_SECRET_KEY = os.environ.get('COS_SECRET_KEY')    # 腾讯云COS的Secret Key
    COS_TOKEN = os.environ.get('COS_TOKEN')              # 如果使用临时密钥，需提供Token；否则为None
    COS_SCHEME = os.environ.get('COS_SCHEME', 'https')   # 访问协议，默认为https