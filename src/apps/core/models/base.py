"""Base models for core"""
from django.db import models
from apps.core.models import TimeStampedModel, AuditModel

class CoreBaseModel(TimeStampedModel):
    """Base model for core app"""
    class Meta:
        abstract = True
