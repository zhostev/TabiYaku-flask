# tests/test_auth.py
import unittest
from app import create_app, db
from app.models import User
import json

class AuthTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_user_registration_and_login(self):
        # Register
        response = self.client.post('/api/auth/register', json={
            'username': 'zho',
            'password': 'zho'
        })
        self.assertEqual(response.status_code, 201)

        # Attempt to register the same user again
        response = self.client.post('/api/auth/register', json={
            'username': 'zho',
            'password': 'zho'
        })
        self.assertEqual(response.status_code, 400)

        # Login with correct credentials
        response = self.client.post('/api/auth/login', json={
            'username': 'zho',
            'password': 'zho'
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('access_token', data)

        # Login with incorrect password
        response = self.client.post('/api/auth/login', json={
            'username': 'zho',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 401)

        # Login with non-existent user
        response = self.client.post('/api/auth/login', json={
            'username': 'nonexistent',
            'password': 'password'
        })
        self.assertEqual(response.status_code, 401)

if __name__ == '__main__':
    unittest.main()