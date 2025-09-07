"""Logging middleware for monitoring"""
from .base import MonitoringBaseMiddleware
import logging

logger = logging.getLogger(__name__)

class LoggingMiddleware(MonitoringBaseMiddleware):
    """Request/response logging"""
    def process_request(self, request):
        logger.info(f"Request: {request.method} {request.path}")
        return None
