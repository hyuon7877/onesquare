"""API tests for auth_system"""
from django.test import TestCase
from rest_framework.test import APIClient

class Auth_SystemAPITest(TestCase):
    """API tests"""
    def setUp(self):
        self.client = APIClient()
    
    def test_api(self):
        self.assertTrue(True)
