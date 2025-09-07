"""Base views for field_reports"""
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin

class Field_ReportsBaseView(LoginRequiredMixin, View):
    """Base view for field_reports app"""
    pass
