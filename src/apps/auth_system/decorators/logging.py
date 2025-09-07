"""Logging middleware for auth_system"""
from .base import Auth_SystemBaseMiddleware
import logging

logger = logging.getLogger(__name__)

class LoggingMiddleware(Auth_SystemBaseMiddleware):
    """Request/response logging"""
    def process_request(self, request):
        logger.info(f"Request: {request.method} {request.path}")
        return None
