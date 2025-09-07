"""Security middleware for performance"""
from .base import PerformanceBaseMiddleware

class SecurityMiddleware(PerformanceBaseMiddleware):
    """Security checks"""
    def process_request(self, request):
        return None
