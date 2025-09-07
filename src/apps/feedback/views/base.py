"""Base views for feedback"""
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin

class FeedbackBaseView(LoginRequiredMixin, View):
    """Base view for feedback app"""
    pass
