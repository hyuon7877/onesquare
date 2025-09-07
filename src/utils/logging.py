"""
Custom logging utilities for OneSquare project
"""

import logging
import json
from datetime import datetime
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging
    """
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'user'):
            log_data['user'] = str(record.user)
        
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        
        if hasattr(record, 'ip_address'):
            log_data['ip_address'] = record.ip_address
        
        return json.dumps(log_data, cls=DjangoJSONEncoder)


class RequestIDMiddleware:
    """
    Middleware to add unique request ID to each request for tracking
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        import uuid
        request.id = str(uuid.uuid4())
        response = self.get_response(request)
        response['X-Request-ID'] = request.id
        return response


def get_client_ip(request):
    """
    Get client IP address from request
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_user_action(logger_name, action, user, request=None, **kwargs):
    """
    Log user actions with context
    
    Args:
        logger_name: Name of the logger to use
        action: Action being performed
        user: User performing the action
        request: Optional HTTP request object
        **kwargs: Additional context to log
    """
    logger = logging.getLogger(logger_name)
    
    extra = {
        'user': user.username if user else 'anonymous',
        'action': action,
    }
    
    if request:
        extra['ip_address'] = get_client_ip(request)
        extra['request_id'] = getattr(request, 'id', None)
        extra['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
    
    extra.update(kwargs)
    
    logger.info(f"User action: {action}", extra=extra)


def log_error(logger_name, error_msg, request=None, exception=None, **kwargs):
    """
    Log errors with context
    
    Args:
        logger_name: Name of the logger to use
        error_msg: Error message
        request: Optional HTTP request object
        exception: Optional exception object
        **kwargs: Additional context to log
    """
    logger = logging.getLogger(logger_name)
    
    extra = {}
    
    if request:
        extra['ip_address'] = get_client_ip(request)
        extra['request_id'] = getattr(request, 'id', None)
        extra['user'] = request.user.username if request.user.is_authenticated else 'anonymous'
        extra['path'] = request.path
        extra['method'] = request.method
    
    extra.update(kwargs)
    
    if exception:
        logger.error(error_msg, exc_info=exception, extra=extra)
    else:
        logger.error(error_msg, extra=extra)


class AuditLogger:
    """
    Specialized logger for audit trails
    """
    
    def __init__(self):
        self.logger = logging.getLogger('audit')
    
    def log_login(self, user, request, success=True):
        """Log login attempts"""
        log_user_action(
            'audit',
            'LOGIN_SUCCESS' if success else 'LOGIN_FAILED',
            user,
            request,
            success=success
        )
    
    def log_logout(self, user, request):
        """Log logout events"""
        log_user_action('audit', 'LOGOUT', user, request)
    
    def log_data_access(self, user, model, action, object_id=None, request=None):
        """Log data access events"""
        log_user_action(
            'audit',
            f'DATA_{action.upper()}',
            user,
            request,
            model=model,
            object_id=object_id
        )
    
    def log_permission_denied(self, user, permission, request=None):
        """Log permission denied events"""
        log_user_action(
            'audit',
            'PERMISSION_DENIED',
            user,
            request,
            permission=permission
        )


# Singleton instance
audit_logger = AuditLogger()