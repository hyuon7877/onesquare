"""View tests for auth_system"""
from django.test import TestCase, Client

class Auth_SystemViewTest(TestCase):
    """View tests"""
    def setUp(self):
        self.client = Client()
    
    def test_views(self):
        self.assertTrue(True)
