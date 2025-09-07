"""Base views for time_management"""
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin

class Time_ManagementBaseView(LoginRequiredMixin, View):
    """Base view for time_management app"""
    pass
