# app/routes/auth.py
from flask_restx import Namespace, Resource, fields
from flask import request
from app import db
from app.models import User
from flask_jwt_extended import create_access_token

auth_ns = Namespace('auth', description='Authentication operations')

register_model = auth_ns.model('Register', {
    'username': fields.String(required=True, description='Username'),
    'password': fields.String(required=True, description='Password'),
})

login_model = auth_ns.model('Login', {
    'username': fields.String(required=True, description='Username'),
    'password': fields.String(required=True, description='Password'),
})

@auth_ns.route('/register')
class Register(Resource):
    @auth_ns.expect(register_model)
    @auth_ns.response(201, 'User registered successfully')
    @auth_ns.response(400, 'Validation Error')
    def post(self):
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return {'msg': 'Username and password are required'}, 400
        
        if User.query.filter_by(username=username).first():
            return {'msg': 'Username already exists'}, 400
        
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        return {'msg': 'User registered successfully'}, 201

@auth_ns.route('/login')
class Login(Resource):
    @auth_ns.expect(login_model)
    @auth_ns.response(200, 'Login successful')
    @auth_ns.response(401, 'Invalid credentials')
    def post(self):
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        user = User.query.filter_by(username=username).first()
        if not user or not user.check_password(password):
            return {'msg': 'Invalid credentials'}, 401
        
        access_token = create_access_token(identity=user.id)
        return {'access_token': access_token}, 200