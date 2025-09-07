"""Base views for monitoring"""
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin

class MonitoringBaseView(LoginRequiredMixin, View):
    """Base view for monitoring app"""
    pass
