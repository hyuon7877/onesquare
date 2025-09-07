"""Base views for ai_analytics"""
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin

class Ai_AnalyticsBaseView(LoginRequiredMixin, View):
    """Base view for ai_analytics app"""
    pass
