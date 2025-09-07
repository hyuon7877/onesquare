"""Logging middleware for performance"""
from .base import PerformanceBaseMiddleware
import logging

logger = logging.getLogger(__name__)

class LoggingMiddleware(PerformanceBaseMiddleware):
    """Request/response logging"""
    def process_request(self, request):
        logger.info(f"Request: {request.method} {request.path}")
        return None
