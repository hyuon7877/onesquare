"""Base views for dashboard"""
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin

class DashboardBaseView(LoginRequiredMixin, View):
    """Base view for dashboard app"""
    pass
