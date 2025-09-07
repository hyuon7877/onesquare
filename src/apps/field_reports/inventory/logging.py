"""Logging middleware for field_reports"""
from .base import Field_ReportsBaseMiddleware
import logging

logger = logging.getLogger(__name__)

class LoggingMiddleware(Field_ReportsBaseMiddleware):
    """Request/response logging"""
    def process_request(self, request):
        logger.info(f"Request: {request.method} {request.path}")
        return None
