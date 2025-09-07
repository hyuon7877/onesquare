"""Base views for revenue"""
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin

class RevenueBaseView(LoginRequiredMixin, View):
    """Base view for revenue app"""
    pass
