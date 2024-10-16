import os

class Config(object):
    # 基础配置
    DEBUG = os.environ.get('FLASK_DEBUG', 'False') == 'True'
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your_secret_key')

    # 数据库配置
    MYSQL_USERNAME = os.environ.get('MYSQL_USERNAME', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'password')
    MYSQL_ADDRESS = os.environ.get('MYSQL_ADDRESS', 'localhost:3306')
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'flask_demo')

    SQLALCHEMY_DATABASE_URI = f"mysql://{MYSQL_USERNAME}:{MYSQL_PASSWORD}@{MYSQL_ADDRESS}/{MYSQL_DATABASE}?charset=utf8mb4"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # OpenAI 配置
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', 'your_openai_api_key')
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4')

    # 上传文件夹
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads/')