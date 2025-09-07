"""Security middleware for field_reports"""
from .base import Field_ReportsBaseMiddleware

class SecurityMiddleware(Field_ReportsBaseMiddleware):
    """Security checks"""
    def process_request(self, request):
        return None
