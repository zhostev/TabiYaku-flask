# app/routes/users.py

from flask_restx import Namespace, Resource, fields
from flask import request
from app import db
from app.models import User
from flask_jwt_extended import (
    jwt_required, get_jwt_identity, create_access_token
)

users_ns = Namespace('users', description='用户相关操作')

# 定义用户模型（用于请求和响应）
user_model = users_ns.model('User', {
    'id': fields.Integer(readOnly=True, description='用户ID'),
    'username': fields.String(required=True, description='用户名'),
    'email': fields.String(required=True, description='用户邮箱')
})

user_create_model = users_ns.model('UserCreate', {
    'username': fields.String(required=True, description='用户名'),
    'email': fields.String(required=True, description='用户邮箱'),
    'password': fields.String(required=True, description='密码')
})

user_update_model = users_ns.model('UserUpdate', {
    'username': fields.String(description='用户名'),
    'email': fields.String(description='用户邮箱'),
    'password': fields.String(description='密码')
})

@users_ns.route('/')
class UserList(Resource):
    @users_ns.marshal_list_with(user_model)
    @jwt_required()
    def get(self):
        """获取所有用户"""
        users = User.query.all()
        return users

    @users_ns.expect(user_create_model)
    @users_ns.marshal_with(user_model, code=201)
    def post(self):
        """创建新用户"""
        data = request.get_json()
        new_user = User(
            username=data['username'],
            email=data['email']
        )
        new_user.set_password(data['password'])
        db.session.add(new_user)
        db.session.commit()
        return new_user, 201

@users_ns.route('/<int:id>')
@users_ns.param('id', '用户ID')
class UserResource(Resource):
    @users_ns.marshal_with(user_model)
    @jwt_required()
    def get(self, id):
        """获取指定用户信息"""
        user = User.query.get_or_404(id)
        return user

    @users_ns.expect(user_update_model)
    @users_ns.marshal_with(user_model)
    @jwt_required()
    def put(self, id):
        """更新指定用户信息"""
        user = User.query.get_or_404(id)
        data = request.get_json()
        if 'username' in data:
            user.username = data['username']
        if 'email' in data:
            user.email = data['email']
        if 'password' in data:
            user.set_password(data['password'])
        db.session.commit()
        return user

    @users_ns.response(204, '用户删除成功')
    @jwt_required()
    def delete(self, id):
        """删除指定用户"""
        user = User.query.get_or_404(id)
        db.session.delete(user)
        db.session.commit()
        return '', 204