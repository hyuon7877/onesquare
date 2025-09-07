"""Base models for monitoring"""
from django.db import models
from apps.core.models import TimeStampedModel, AuditModel

class MonitoringBaseModel(TimeStampedModel):
    """Base model for monitoring app"""
    class Meta:
        abstract = True
