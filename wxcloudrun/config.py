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

    # OpenAI 配置
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', 'your_openai_api_key')
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4')

    # 上传文件夹
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/app/uploads/')

    # 腾讯云COS配置
    COS_BUCKET = os.environ.get('COS_BUCKET')
    COS_REGION = os.environ.get('COS_REGION')
    COS_SECRET_ID = os.environ.get('COS_SECRET_ID')  # 新增: 腾讯云COS的Secret ID
    COS_SECRET_KEY = os.environ.get('COS_SECRET_KEY')  # 新增: 腾讯云COS的Secret Key