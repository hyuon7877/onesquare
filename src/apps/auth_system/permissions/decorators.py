"""
권한 확인 데코레이터
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from .user import has_permission
from .base import logger

def require_permission(permission_code):
    """권한 확인 데코레이터"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "로그인이 필요합니다.")
                return redirect('login')
            
            if not has_permission(request.user, permission_code):
                logger.warning(f"권한 거부: {request.user.username} - {permission_code}")
                raise PermissionDenied(f"'{permission_code}' 권한이 필요합니다.")
            
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator

def require_any_permission(*permission_codes):
    """여러 권한 중 하나라도 있으면 허용"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "로그인이 필요합니다.")
                return redirect('login')
            
            for permission_code in permission_codes:
                if has_permission(request.user, permission_code):
                    return view_func(request, *args, **kwargs)
            
            logger.warning(f"권한 거부: {request.user.username} - {permission_codes}")
            raise PermissionDenied(f"다음 권한 중 하나가 필요합니다: {', '.join(permission_codes)}")
        return wrapped_view
    return decorator

def require_all_permissions(*permission_codes):
    """모든 권한을 가져야 허용"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "로그인이 필요합니다.")
                return redirect('login')
            
            for permission_code in permission_codes:
                if not has_permission(request.user, permission_code):
                    logger.warning(f"권한 거부: {request.user.username} - {permission_code}")
                    raise PermissionDenied(f"모든 권한이 필요합니다: {', '.join(permission_codes)}")
            
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator
