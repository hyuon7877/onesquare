"""Base models for auth_system"""
from django.db import models
from apps.core.models import TimeStampedModel, AuditModel

class Auth_SystemBaseModel(TimeStampedModel):
    """Base model for auth_system app"""
    class Meta:
        abstract = True
