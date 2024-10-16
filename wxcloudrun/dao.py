from . import db
from .model import TranslationRecord
from sqlalchemy.exc import SQLAlchemyError
from wxcloudrun.model import Counters

def insert_translation_record(image_path, chinese_translation, user_id):
    try:
        record = TranslationRecord(
            image_path=image_path,
            chinese_translation=chinese_translation,
            user_id=user_id
        )
        db.session.add(record)
        db.session.commit()
        return record
    except SQLAlchemyError as e:
        db.session.rollback()
        # 记录详细错误信息
        current_app.logger.error(f"Database Insert Error: {e}")
        raise

