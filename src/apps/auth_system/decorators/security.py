"""Security middleware for auth_system"""
from .base import Auth_SystemBaseMiddleware

class SecurityMiddleware(Auth_SystemBaseMiddleware):
    """Security checks"""
    def process_request(self, request):
        return None
