"""Base models for field_reports"""
from django.db import models
from apps.core.models import TimeStampedModel, AuditModel

class Field_ReportsBaseModel(TimeStampedModel):
    """Base model for field_reports app"""
    class Meta:
        abstract = True
