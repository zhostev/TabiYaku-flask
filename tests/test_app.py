# tests/test_app.py
import unittest
from app import create_app, db
from app.models import User
from flask import url_for
import json

class TabiYakuTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            user = User(username='testuser')
            user.set_password('testpass')
            db.session.add(user)
            db.session.commit()
    
    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_register(self):
        response = self.client.post('/api/auth/register', json={
            'username': 'newuser',
            'password': 'newpass'
        })
        self.assertEqual(response.status_code, 201)
    
    def test_login(self):
        response = self.client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'testpass'
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('access_token', data)

if __name__ == '__main__':
    unittest.main()