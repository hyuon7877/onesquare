"""Base models for dashboard"""
from django.db import models
from apps.core.models import TimeStampedModel, AuditModel

class DashboardBaseModel(TimeStampedModel):
    """Base model for dashboard app"""
    class Meta:
        abstract = True
