"""Base views for calendar_system"""
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin

class Calendar_SystemBaseView(LoginRequiredMixin, View):
    """Base view for calendar_system app"""
    pass
