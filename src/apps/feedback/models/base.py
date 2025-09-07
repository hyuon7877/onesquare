"""Base models for feedback"""
from django.db import models
from apps.core.models import TimeStampedModel, AuditModel

class FeedbackBaseModel(TimeStampedModel):
    """Base model for feedback app"""
    class Meta:
        abstract = True
