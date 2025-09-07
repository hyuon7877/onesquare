"""Security middleware for dashboard"""
from .base import DashboardBaseMiddleware

class SecurityMiddleware(DashboardBaseMiddleware):
    """Security checks"""
    def process_request(self, request):
        return None
