"""Base models for revenue"""
from django.db import models
from apps.core.models import TimeStampedModel, AuditModel

class RevenueBaseModel(TimeStampedModel):
    """Base model for revenue app"""
    class Meta:
        abstract = True
