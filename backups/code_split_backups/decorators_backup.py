"""
OneSquare 사용자 인증 시스템 - 권한 및 보안 데코레이터

이 모듈은 뷰 함수나 클래스에 적용할 수 있는 사용자 권한 검증 데코레이터들을 제공합니다.
"""

from functools import wraps
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status
import logging

from .models import UserType
from .utils import UserPermissionChecker

logger = logging.getLogger(__name__)


def user_type_required(allowed_user_types):
    """
    특정 사용자 타입만 접근 가능하도록 제한하는 데코레이터
    
    Args:
        allowed_user_types: 허용된 사용자 타입 리스트 또는 단일 타입
        
    Usage:
        @user_type_required([UserType.SUPER_ADMIN, UserType.MANAGER])
        def admin_view(request):
            pass
    """
    if not isinstance(allowed_user_types, (list, tuple)):
        allowed_user_types = [allowed_user_types]
    
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({
                    'error': '로그인이 필요합니다.'
                }, status=401)
            
            if request.user.user_type not in allowed_user_types:
                logger.warning(
                    f"권한 없는 접근 시도: {request.user.username} "
                    f"(타입: {request.user.user_type}) -> {view_func.__name__}"
                )
                return JsonResponse({
                    'error': '접근 권한이 없습니다.',
                    'required_user_types': [str(ut) for ut in allowed_user_types]
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def permission_required(permission_check_func, error_message=None):
    """
    커스텀 권한 체크 함수를 사용하는 데코레이터
    
    Args:
        permission_check_func: 사용자 객체를 받아 bool을 반환하는 함수
        error_message: 권한 없을 때 표시할 메시지
        
    Usage:
        @permission_required(UserPermissionChecker.can_manage_users)
        def user_management_view(request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({
                    'error': '로그인이 필요합니다.'
                }, status=401)
            
            if not permission_check_func(request.user):
                logger.warning(
                    f"권한 체크 실패: {request.user.username} -> {view_func.__name__}"
                )
                return JsonResponse({
                    'error': error_message or '접근 권한이 없습니다.'
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def approved_user_required(view_func):
    """
    승인된 사용자만 접근 가능하도록 제한하는 데코레이터
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'error': '로그인이 필요합니다.'
            }, status=401)
        
        if not request.user.is_approved:
            logger.warning(f"미승인 사용자 접근 시도: {request.user.username}")
            return JsonResponse({
                'error': '승인되지 않은 계정입니다. 관리자에게 문의하세요.'
            }, status=403)
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def active_user_required(view_func):
    """
    활성 사용자만 접근 가능하도록 제한하는 데코레이터
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'error': '로그인이 필요합니다.'
            }, status=401)
        
        if not request.user.is_active:
            logger.warning(f"비활성 사용자 접근 시도: {request.user.username}")
            return JsonResponse({
                'error': '비활성화된 계정입니다.'
            }, status=403)
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def admin_required(view_func):
    """
    관리자 권한 필요 데코레이터
    """
    @wraps(view_func)
    @permission_required(
        UserPermissionChecker.can_manage_users,
        "관리자 권한이 필요합니다."
    )
    def _wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def dashboard_access_required(view_func):
    """
    대시보드 접근 권한 필요 데코레이터
    """
    @wraps(view_func)
    @permission_required(
        UserPermissionChecker.has_dashboard_access,
        "대시보드 접근 권한이 없습니다."
    )
    def _wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def reports_access_required(view_func):
    """
    리포트 조회 권한 필요 데코레이터
    """
    @wraps(view_func)
    @permission_required(
        UserPermissionChecker.can_view_reports,
        "리포트 조회 권한이 없습니다."
    )
    def _wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def field_reports_access_required(view_func):
    """
    현장 리포트 접근 권한 필요 데코레이터
    """
    @wraps(view_func)
    @permission_required(
        UserPermissionChecker.can_access_field_reports,
        "현장 리포트 접근 권한이 없습니다."
    )
    def _wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return _wrapped_view


class CSRFExemptMixin:
    """
    특정 API 엔드포인트에서 CSRF 보호를 비활성화하는 믹스인
    (주로 외부 API 통합이나 특별한 경우에만 사용)
    """
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class SecureApiMixin:
    """
    API 보안을 강화하는 믹스인
    - CSRF 보호
    - 사용자 승인 상태 확인
    - 활성 사용자 확인
    """
    
    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        # 사용자 인증 상태 확인
        if hasattr(request, 'user') and request.user.is_authenticated:
            # 승인 상태 확인
            if not request.user.is_approved:
                return JsonResponse({
                    'error': '승인되지 않은 계정입니다.'
                }, status=403)
            
            # 활성 상태 확인
            if not request.user.is_active:
                return JsonResponse({
                    'error': '비활성화된 계정입니다.'
                }, status=403)
        
        return super().dispatch(request, *args, **kwargs)


def rate_limit_by_user(max_requests=10, time_window=60):
    """
    사용자별 API 요청 제한 데코레이터
    
    Args:
        max_requests: 시간 창 내 최대 요청 수
        time_window: 시간 창 (초)
    """
    from django.core.cache import cache
    from django.utils import timezone
    import hashlib
    
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return view_func(request, *args, **kwargs)
            
            # 사용자별 캐시 키 생성
            cache_key = f"rate_limit_{hashlib.md5(str(request.user.id).encode()).hexdigest()}_{view_func.__name__}"
            
            # 현재 요청 수 확인
            current_requests = cache.get(cache_key, 0)
            
            if current_requests >= max_requests:
                logger.warning(
                    f"Rate limit 초과: {request.user.username} -> {view_func.__name__}"
                )
                return JsonResponse({
                    'error': f'요청 한도를 초과했습니다. {time_window}초 후 다시 시도해주세요.',
                    'rate_limit': {
                        'max_requests': max_requests,
                        'time_window': time_window,
                        'current_requests': current_requests
                    }
                }, status=429)
            
            # 요청 수 증가
            cache.set(cache_key, current_requests + 1, time_window)
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def log_user_action(action_description=""):
    """
    사용자 액션을 로그에 기록하는 데코레이터
    
    Args:
        action_description: 액션 설명
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated:
                logger.info(
                    f"사용자 액션: {request.user.username} -> "
                    f"{action_description or view_func.__name__} "
                    f"(IP: {request.META.get('REMOTE_ADDR', 'unknown')})"
                )
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


# 클래스 기반 뷰용 데코레이터들

class UserTypeRequiredMixin:
    """
    클래스 기반 뷰에서 사용자 타입 제한을 위한 믹스인
    """
    required_user_types = None
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'error': '로그인이 필요합니다.'
            }, status=401)
        
        if (self.required_user_types and 
            request.user.user_type not in self.required_user_types):
            return JsonResponse({
                'error': '접근 권한이 없습니다.'
            }, status=403)
        
        return super().dispatch(request, *args, **kwargs)


class AdminRequiredMixin:
    """
    관리자 권한이 필요한 클래스 기반 뷰용 믹스인
    """
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'error': '로그인이 필요합니다.'
            }, status=401)
        
        if not UserPermissionChecker.can_manage_users(request.user):
            return JsonResponse({
                'error': '관리자 권한이 필요합니다.'
            }, status=403)
        
        return super().dispatch(request, *args, **kwargs)


# 조합된 데코레이터들 (자주 사용되는 조합)

def secure_api_view(view_func):
    """
    보안이 강화된 API 뷰 데코레이터 (로그인 + 승인 + 활성 체크)
    """
    @wraps(view_func)
    @login_required
    @approved_user_required
    @active_user_required
    def _wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def admin_api_view(view_func):
    """
    관리자용 API 뷰 데코레이터
    """
    @wraps(view_func)
    @secure_api_view
    @admin_required
    def _wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def partner_api_view(view_func):
    """
    파트너/도급사용 API 뷰 데코레이터
    """
    @wraps(view_func)
    @user_type_required([UserType.PARTNER, UserType.CONTRACTOR])
    @approved_user_required
    @active_user_required
    def _wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def staff_api_view(view_func):
    """
    직원(관리자/중간관리자/팀원)용 API 뷰 데코레이터
    """
    @wraps(view_func)
    @user_type_required([UserType.SUPER_ADMIN, UserType.MANAGER, UserType.TEAM_MEMBER])
    @active_user_required
    def _wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def ajax_required(view_func):
    """
    AJAX 요청만 허용하는 데코레이터
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'error': 'AJAX 요청만 허용됩니다.'
            }, status=400)
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def api_key_required(view_func):
    """
    API 키가 필요한 외부 API 엔드포인트용 데코레이터
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.GET.get('api_key')
        
        if not api_key:
            return JsonResponse({
                'error': 'API 키가 필요합니다.',
                'code': 'API_KEY_MISSING'
            }, status=401)
        
        # API 키 검증 로직 (실제 구현에서는 데이터베이스에서 확인)
        valid_api_keys = getattr(settings, 'VALID_API_KEYS', [])
        
        if api_key not in valid_api_keys:
            logger.warning(f"잘못된 API 키 사용 시도: {api_key[:10]}... from {request.META.get('REMOTE_ADDR')}")
            return JsonResponse({
                'error': '유효하지 않은 API 키입니다.',
                'code': 'API_KEY_INVALID'
            }, status=401)
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def method_required(*allowed_methods):
    """
    특정 HTTP 메서드만 허용하는 데코레이터
    
    Usage:
        @method_required('GET', 'POST')
        def my_view(request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.method not in allowed_methods:
                return JsonResponse({
                    'error': f'허용되지 않은 HTTP 메서드입니다. 허용된 메서드: {", ".join(allowed_methods)}',
                    'allowed_methods': list(allowed_methods)
                }, status=405)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def content_type_required(content_type='application/json'):
    """
    특정 Content-Type을 요구하는 데코레이터
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.content_type != content_type:
                return JsonResponse({
                    'error': f'Content-Type이 {content_type}이어야 합니다.',
                    'received_content_type': request.content_type
                }, status=400)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def otp_authenticated_required(view_func):
    """
    OTP 인증이 완료된 상태에서만 접근 가능한 데코레이터
    (보안이 중요한 작업용)
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        # OTP 인증이 필요한 사용자 타입인지 확인
        if request.user.user_type in [UserType.PARTNER, UserType.CONTRACTOR]:
            # 세션에서 OTP 인증 여부 확인
            if not request.session.get('otp_verified', False):
                return JsonResponse({
                    'error': 'OTP 인증이 필요합니다.',
                    'otp_required': True
                }, status=403)
            
            # OTP 인증 시간 확인 (30분 제한)
            otp_verified_at = request.session.get('otp_verified_at')
            if otp_verified_at:
                from django.utils import timezone
                import datetime
                try:
                    verified_time = datetime.datetime.fromisoformat(otp_verified_at)
                    if (timezone.now() - verified_time).total_seconds() > 1800:  # 30분
                        request.session['otp_verified'] = False
                        return JsonResponse({
                            'error': 'OTP 인증이 만료되었습니다. 다시 인증해주세요.',
                            'otp_expired': True
                        }, status=403)
                except (ValueError, TypeError):
                    request.session['otp_verified'] = False
                    return JsonResponse({
                        'error': 'OTP 인증 정보가 올바르지 않습니다.',
                        'otp_required': True
                    }, status=403)
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view