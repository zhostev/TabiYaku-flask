# tests/test_users.py

import unittest
from app import create_app, db
from app.models import User
from flask_jwt_extended import create_access_token

class UserTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # 使用内存数据库进行测试
        self.app.config['TESTING'] = True
        self.app.config['JWT_SECRET_KEY'] = 'test-secret-key'
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            # 创建一个测试用户
            user = User(username='testuser', email='test@example.com')
            user.set_password('testpassword')
            db.session.add(user)
            db.session.commit()
            self.user_id = user.id
            self.access_token = create_access_token(identity=self.user_id)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_get_users(self):
        response = self.client.get(
            '/api/users/',
            headers={'Authorization': f'Bearer {self.access_token}'}
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['username'], 'testuser')

    def test_create_user(self):
        new_user = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'newpassword'
        }
        response = self.client.post('/api/users/', json=new_user)
        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data['username'], 'newuser')
        self.assertEqual(data['email'], 'new@example.com')

    def test_get_user(self):
        response = self.client.get(
            f'/api/users/{self.user_id}',
            headers={'Authorization': f'Bearer {self.access_token}'}
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['username'], 'testuser')

    def test_update_user(self):
        updated_data = {
            'username': 'updateduser'
        }
        response = self.client.put(
            f'/api/users/{self.user_id}',
            json=updated_data,
            headers={'Authorization': f'Bearer {self.access_token}'}
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['username'], 'updateduser')

    def test_delete_user(self):
        response = self.client.delete(
            f'/api/users/{self.user_id}',
            headers={'Authorization': f'Bearer {self.access_token}'}
        )
        self.assertEqual(response.status_code, 204)

        # 确认用户已被删除
        response = self.client.get(
            f'/api/users/{self.user_id}',
            headers={'Authorization': f'Bearer {self.access_token}'}
        )
        self.assertEqual(response.status_code, 404)

if __name__ == '__main__':
    unittest.main()