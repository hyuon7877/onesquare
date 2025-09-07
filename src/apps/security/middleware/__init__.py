"""OneSquare 보안 미들웨어 패키지

분할된 보안 미들웨어 모듈 통합
"""

from .headers import SecurityHeadersMiddleware
from .validation import InputValidationMiddleware
from .authentication import (
    AuthenticationEnhancementMiddleware,
    SessionSecurityMiddleware,
)
from .rate_limiting import RateLimitingMiddleware
from .intrusion_detection import IntrusionDetectionMiddleware
from .audit_logging import AuditLoggingMiddleware
from .csrf_protection import EnhancedCSRFMiddleware

__all__ = [
    'SecurityHeadersMiddleware',
    'InputValidationMiddleware',
    'AuthenticationEnhancementMiddleware',
    'SessionSecurityMiddleware',
    'RateLimitingMiddleware',
    'IntrusionDetectionMiddleware',
    'AuditLoggingMiddleware',
    'EnhancedCSRFMiddleware',
]

# 미들웨어 등록 순서 (settings.py MIDDLEWARE 설정용)
MIDDLEWARE_ORDER = [
    'apps.security.middleware.SecurityHeadersMiddleware',
    'apps.security.middleware.RateLimitingMiddleware',
    'apps.security.middleware.IntrusionDetectionMiddleware',
    'apps.security.middleware.InputValidationMiddleware',
    'apps.security.middleware.EnhancedCSRFMiddleware',
    'apps.security.middleware.AuthenticationEnhancementMiddleware',
    'apps.security.middleware.SessionSecurityMiddleware',
    'apps.security.middleware.AuditLoggingMiddleware',
]
