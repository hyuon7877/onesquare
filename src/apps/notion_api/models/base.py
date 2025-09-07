"""Base models for notion_api"""
from django.db import models
from apps.core.models import TimeStampedModel, AuditModel

class Notion_ApiBaseModel(TimeStampedModel):
    """Base model for notion_api app"""
    class Meta:
        abstract = True
