"""Base models for calendar_system"""
from django.db import models
from apps.core.models import TimeStampedModel, AuditModel

class Calendar_SystemBaseModel(TimeStampedModel):
    """Base model for calendar_system app"""
    class Meta:
        abstract = True
