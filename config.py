import os

DEBUG = os.environ.get('FLASK_ENV') == 'development'
SECRET_KEY = os.environ.get('SECRET_KEY', 'your_secret_key')

# Database Configuration
MYSQL_USERNAME = os.environ.get('MYSQL_USERNAME', 'halo_4cSd4J')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'Moshou99')
MYSQL_ADDRESS = os.environ.get('MYSQL_ADDRESS', 'rm-2zev5u696jj316m801o.mysql.rds.aliyuncs.com:3306')
SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{MYSQL_USERNAME}:{MYSQL_PASSWORD}@{MYSQL_ADDRESS}/flask_demo"
SQLALCHEMY_TRACK_MODIFICATIONS = False

# JWT Configuration
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your_jwt_secret_key')

# OpenAI Configuration
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', 'your_openai_api_key')
OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4')
OPENAI_API_BASE = os.environ.get('OPENAI_API_BASE', 'https://lsapi.zeabur.app/v1')

# Upload Folder (Updated to Relative Path)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', os.path.join(BASE_DIR, 'uploads'))

# Flask-Login Configuration
LOGIN_URL = '/auth/login'  # 根据你的路由调整

# Swagger Configuration (if using Flask-RESTX)
SWAGGER = {
    'title': 'TabiYaku API',
    'uiversion': 3
}