"""Base models for ai_analytics"""
from django.db import models
from apps.core.models import TimeStampedModel, AuditModel

class Ai_AnalyticsBaseModel(TimeStampedModel):
    """Base model for ai_analytics app"""
    class Meta:
        abstract = True
