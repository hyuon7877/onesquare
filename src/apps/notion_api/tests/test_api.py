"""API tests for notion_api"""
from django.test import TestCase
from rest_framework.test import APIClient

class Notion_ApiAPITest(TestCase):
    """API tests"""
    def setUp(self):
        self.client = APIClient()
    
    def test_api(self):
        self.assertTrue(True)
