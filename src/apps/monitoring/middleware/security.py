"""Security middleware for monitoring"""
from .base import MonitoringBaseMiddleware

class SecurityMiddleware(MonitoringBaseMiddleware):
    """Security checks"""
    def process_request(self, request):
        return None
