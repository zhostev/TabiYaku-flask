# app/routes/translate.py
from flask_restx import Namespace, Resource, fields
from flask import request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Translation, User
from app import db
from app.utils.image_processing import encode_image, compress_image
from app.utils.translation import translate_recipe
import os

translate_ns = Namespace('translate', description='Translation operations')

translation_model = translate_ns.model('Translation', {
    'id': fields.Integer(readonly=True, description='Translation ID'),
    'original_text': fields.String(description='Original Japanese text'),
    'translated_text': fields.String(description='Translated Chinese text'),
    'image_url': fields.String(description='URL of the uploaded image'),
    'created_at': fields.DateTime(description='Creation timestamp'),
})

@translate_ns.route('/translate')
class Translate(Resource):
    @jwt_required()
    @translate_ns.expect(translate_ns.parser()
        .add_argument('text', type=str, location='form', required=False, help='Original Japanese text')
        .add_argument('file', type='file', location='files', required=False, help='Image file of the Japanese recipe'))
    @translate_ns.marshal_with(translation_model)
    def post(self):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user:
            return {'msg': 'User not found'}, 404
        
        text = request.form.get('text')
        file = request.files.get('file')
        image_base64 = None
        image_path = None
        
        if file:
            filename = file.filename
            upload_folder = current_app.config['UPLOAD_FOLDER']
            image_path = os.path.join(upload_folder, filename)
            file.save(image_path)
            
            # Optionally compress the image
            compressed_path = os.path.join(upload_folder, f"compressed_{filename}")
            compress_image(image_path, compressed_path)
            image_base64 = encode_image(compressed_path)
        
        if not text and not image_base64:
            return {'msg': 'No text or image provided for translation'}, 400
        
        translated_text = translate_recipe(text if text else "", image_base64)
        
        # Save translation record
        translation = Translation(
            original_text=text if text else '',
            translated_text=translated_text,
            image_path=image_path,
            user_id=user_id
        )
        db.session.add(translation)
        db.session.commit()
        
        response = {
            'id': translation.id,
            'original_text': text if text else '',
            'translated_text': translated_text,
            'image_url': f"/api/uploads/{filename}" if image_path else None,
            'created_at': translation.created_at
        }
        
        return response, 200

@translate_ns.route('/uploads/<filename>')
class UploadedFile(Resource):
    def get(self, filename):
        return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
    
@translate_ns.route('/translations')
class Translations(Resource):
    @jwt_required()
    @translate_ns.marshal_list_with(translation_model)
    def get(self):
        user_id = get_jwt_identity()
        translations = Translation.query.filter_by(user_id=user_id).order_by(Translation.created_at.desc()).all()
        result = []
        for t in translations:
            result.append({
                'id': t.id,
                'original_text': t.original_text,
                'translated_text': t.translated_text,
                'image_url': f"/api/uploads/{os.path.basename(t.image_path)}" if t.image_path else None,
                'created_at': t.created_at
            })
        return result, 200