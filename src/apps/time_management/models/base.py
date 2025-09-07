"""Base models for time_management"""
from django.db import models
from apps.core.models import TimeStampedModel, AuditModel

class Time_ManagementBaseModel(TimeStampedModel):
    """Base model for time_management app"""
    class Meta:
        abstract = True
