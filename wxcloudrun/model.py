from . import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'  # 指定表名，避免与 MySQL 保留字冲突
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)  # 哈希后的密码
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    translations = db.relationship('TranslationRecord', backref='user', lazy=True)

class TranslationRecord(db.Model):
    __tablename__ = 'translation_records'
    id = db.Column(db.Integer, primary_key=True)
    image_path = db.Column(db.String(200), nullable=False)
    chinese_translation = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)