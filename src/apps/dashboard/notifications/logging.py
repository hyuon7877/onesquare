"""Logging middleware for dashboard"""
from .base import DashboardBaseMiddleware
import logging

logger = logging.getLogger(__name__)

class LoggingMiddleware(DashboardBaseMiddleware):
    """Request/response logging"""
    def process_request(self, request):
        logger.info(f"Request: {request.method} {request.path}")
        return None
