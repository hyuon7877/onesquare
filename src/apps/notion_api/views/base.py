"""Base views for notion_api"""
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin

class Notion_ApiBaseView(LoginRequiredMixin, View):
    """Base view for notion_api app"""
    pass
