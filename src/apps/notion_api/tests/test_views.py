"""View tests for notion_api"""
from django.test import TestCase, Client

class Notion_ApiViewTest(TestCase):
    """View tests"""
    def setUp(self):
        self.client = Client()
    
    def test_views(self):
        self.assertTrue(True)
