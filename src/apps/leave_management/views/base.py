"""Base views for leave_management"""
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin

class Leave_ManagementBaseView(LoginRequiredMixin, View):
    """Base view for leave_management app"""
    pass
