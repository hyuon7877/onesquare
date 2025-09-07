"""보안 헤더 설정 미들웨어"""
import logging
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('apps.security')


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    보안 헤더 설정 미들웨어
    - Content Security Policy (CSP)
    - HTTP Strict Transport Security (HSTS)
    - X-Frame-Options
    - X-Content-Type-Options
    - Referrer-Policy
    - Permissions-Policy
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.is_debug = getattr(settings, 'DEBUG', False)
    
    def process_response(self, request, response):
        """보안 헤더 추가"""
        
        # Content Security Policy (CSP)
        if not self.is_debug:
            csp = "; ".join([
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
                "font-src 'self' https://fonts.gstatic.com",
                "img-src 'self' data: https:",
                "connect-src 'self' https://api.notion.com",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'"
            ])
            response['Content-Security-Policy'] = csp
        
        # Strict Transport Security
        if not self.is_debug:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        # X-Frame-Options
        response['X-Frame-Options'] = 'DENY'
        
        # X-Content-Type-Options
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy
        permissions = [
            'geolocation=()',
            'microphone=()',
            'camera=()',
            'payment=()',
            'usb=()',
            'magnetometer=()',
            'gyroscope=()',
            'accelerometer=()'
        ]
        response['Permissions-Policy'] = ', '.join(permissions)
        
        # X-XSS-Protection (레거시 브라우저용)
        response['X-XSS-Protection'] = '1; mode=block'
        
        return response
