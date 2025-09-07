"""Base views for auth_system"""
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin

class Auth_SystemBaseView(LoginRequiredMixin, View):
    """Base view for auth_system app"""
    pass
