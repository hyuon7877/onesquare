"""Base views for pwa"""
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin

class PwaBaseView(LoginRequiredMixin, View):
    """Base view for pwa app"""
    pass
