"""
OneSquare 사용자 인증 시스템 - 커스텀 미들웨어

이 모듈은 인증, 보안, 세션 관리를 위한 커스텀 미들웨어들을 제공합니다.
"""

import json
import logging
from datetime import datetime
from django.http import JsonResponse
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import logout
from django.core.cache import cache
from django.conf import settings
import hashlib

from .models import UserSession, CustomUser
from .utils import SessionManager

logger = logging.getLogger(__name__)


class UserSessionMiddleware(MiddlewareMixin):
    """
    사용자 세션을 추적하고 관리하는 미들웨어
    
    기능:
    - 로그인한 사용자의 세션 정보 업데이트
    - 중복 로그인 감지 및 처리
    - 세션 활동 시간 추적
    """
    
    def process_request(self, request):
        if (request.user.is_authenticated and 
            hasattr(request, 'session') and 
            request.session.session_key):
            
            try:
                # 현재 세션 정보 업데이트
                user_session, created = UserSession.objects.get_or_create(
                    user=request.user,
                    session_key=request.session.session_key,
                    defaults={
                        'ip_address': request.META.get('REMOTE_ADDR', ''),
                        'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
                        'is_active': True,
                    }
                )
                
                if not created:
                    # 기존 세션의 마지막 활동 시간 업데이트
                    user_session.update_last_activity()
                
                # 중복 로그인 체크 (설정에 따라)
                if getattr(settings, 'ALLOW_MULTIPLE_SESSIONS', True):
                    # 다중 세션 허용 - 오래된 세션만 정리
                    max_sessions = getattr(settings, 'MAX_SESSIONS_PER_USER', 3)
                    active_sessions = UserSession.objects.filter(
                        user=request.user,
                        is_active=True
                    ).order_by('-last_activity')
                    
                    if active_sessions.count() > max_sessions:
                        # 가장 오래된 세션들 비활성화
                        old_sessions = active_sessions[max_sessions:]
                        for old_session in old_sessions:
                            old_session.is_active = False
                            old_session.save()
                            
                        logger.info(f"사용자 {request.user.username}의 오래된 세션 {len(old_sessions)}개 정리")
                
                else:
                    # 단일 세션만 허용 - 다른 세션들 비활성화
                    other_sessions = UserSession.objects.filter(
                        user=request.user,
                        is_active=True
                    ).exclude(session_key=request.session.session_key)
                    
                    if other_sessions.exists():
                        other_sessions.update(is_active=False)
                        logger.info(f"사용자 {request.user.username}의 다중 로그인 감지 - 기존 세션 종료")
                
            except Exception as e:
                logger.error(f"세션 미들웨어 오류: {e}")
        
        return None


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    보안 헤더를 추가하는 미들웨어
    
    PWA 및 API 보안을 위한 다양한 HTTP 헤더 설정
    """
    
    def process_response(self, request, response):
        # PWA를 위한 보안 헤더들
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # PWA 매니페스트 및 서비스 워커를 위한 CORS 설정
        if request.path in ['/manifest.json', '/sw.js']:
            response['Cross-Origin-Embedder-Policy'] = 'unsafe-none'
        
        # API 응답에 대한 캐시 제어
        if request.path.startswith('/api/'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            
            # API 응답에 CORS 헤더 추가 (PWA용)
            if hasattr(settings, 'CORS_ALLOWED_ORIGINS'):
                origin = request.META.get('HTTP_ORIGIN')
                if origin in settings.CORS_ALLOWED_ORIGINS:
                    response['Access-Control-Allow-Credentials'] = 'true'
        
        return response


class APIRateLimitMiddleware(MiddlewareMixin):
    """
    API 요청 제한 미들웨어
    
    사용자별, IP별 요청 제한을 통한 DDoS 방지
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limit_settings = {
            # API 경로별 제한 설정 (요청/분)
            '/api/auth/login/': {'limit': 5, 'window': 300},  # 5회/5분
            '/api/auth/otp/request/': {'limit': 3, 'window': 300},  # 3회/5분
            '/api/auth/register/': {'limit': 2, 'window': 3600},  # 2회/1시간
            'default': {'limit': 100, 'window': 60},  # 기본: 100회/분
        }
    
    def process_request(self, request):
        # API 요청이 아니면 통과
        if not request.path.startswith('/api/'):
            return None
        
        # 요청 제한 확인
        rate_limit_exceeded, remaining_time = self._check_rate_limit(request)
        
        if rate_limit_exceeded:
            logger.warning(
                f"Rate limit 초과: {self._get_client_identifier(request)} -> {request.path}"
            )
            return JsonResponse({
                'error': 'Too many requests',
                'message': f'{remaining_time}초 후 다시 시도해주세요.',
                'retry_after': remaining_time
            }, status=429)
        
        return None
    
    def _check_rate_limit(self, request):
        """요청 제한 확인"""
        client_id = self._get_client_identifier(request)
        path = request.path
        
        # 경로별 제한 설정 가져오기
        limit_config = self.rate_limit_settings.get(path, self.rate_limit_settings['default'])
        max_requests = limit_config['limit']
        time_window = limit_config['window']
        
        # 캐시 키 생성
        cache_key = f"rate_limit:{hashlib.md5(client_id.encode()).hexdigest()}:{path}"
        
        # 현재 요청 수 확인
        current_requests = cache.get(cache_key, 0)
        
        if current_requests >= max_requests:
            # 제한 초과 - 남은 시간 계산
            ttl = cache.ttl(cache_key)
            return True, max(ttl, 0)
        
        # 요청 수 증가
        cache.set(cache_key, current_requests + 1, time_window)
        return False, 0
    
    def _get_client_identifier(self, request):
        """클라이언트 식별자 생성"""
        if request.user.is_authenticated:
            return f"user:{request.user.id}"
        else:
            # IP 주소 기반 식별
            ip_address = request.META.get('HTTP_X_FORWARDED_FOR')
            if ip_address:
                ip_address = ip_address.split(',')[0].strip()
            else:
                ip_address = request.META.get('REMOTE_ADDR', 'unknown')
            return f"ip:{ip_address}"


class UserActivityLoggingMiddleware(MiddlewareMixin):
    """
    사용자 활동 로깅 미들웨어
    
    중요한 API 호출 및 사용자 행동을 로그에 기록
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.logged_paths = [
            '/api/auth/',
            '/api/admin/',
            '/api/reports/',
            '/api/dashboard/',
        ]
    
    def process_request(self, request):
        # 로깅 대상 경로 확인
        should_log = any(request.path.startswith(path) for path in self.logged_paths)
        
        if should_log and request.user.is_authenticated:
            # 요청 정보 로깅
            log_data = {
                'user': request.user.username,
                'user_id': request.user.id,
                'path': request.path,
                'method': request.method,
                'ip_address': request.META.get('REMOTE_ADDR', 'unknown'),
                'user_agent': request.META.get('HTTP_USER_AGENT', 'unknown')[:200],
                'timestamp': timezone.now().isoformat(),
            }
            
            # POST 데이터가 있는 경우 (민감 정보 제외)
            if request.method == 'POST' and request.content_type == 'application/json':
                try:
                    post_data = json.loads(request.body.decode('utf-8'))
                    # 민감 정보 제거
                    sensitive_fields = ['password', 'otp_code', 'token']
                    for field in sensitive_fields:
                        if field in post_data:
                            post_data[field] = '***'
                    log_data['post_data'] = post_data
                except:
                    pass
            
            logger.info(f"User Activity: {json.dumps(log_data, ensure_ascii=False)}")
        
        return None


class CSRFFailureMiddleware(MiddlewareMixin):
    """
    CSRF 실패를 처리하는 미들웨어
    
    CSRF 토큰 오류 시 친화적인 응답 제공
    """
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        return None
    
    def process_exception(self, request, exception):
        # CSRF 오류 처리
        if hasattr(exception, '__class__') and 'Forbidden' in str(exception.__class__):
            if request.path.startswith('/api/'):
                return JsonResponse({
                    'error': 'CSRF verification failed',
                    'message': 'CSRF 토큰이 유효하지 않습니다. 페이지를 새로고침하고 다시 시도해주세요.',
                    'code': 'CSRF_FAILURE'
                }, status=403)
        
        return None


class MaintenanceModeMiddleware(MiddlewareMixin):
    """
    유지보수 모드 미들웨어
    
    시스템 점검 시 모든 요청을 차단하고 안내 메시지 표시
    """
    
    def process_request(self, request):
        maintenance_mode = getattr(settings, 'MAINTENANCE_MODE', False)
        
        if maintenance_mode:
            # 관리자는 접근 허용
            if (request.user.is_authenticated and 
                (request.user.is_superuser or request.path.startswith('/admin/'))):
                return None
            
            # API 요청인 경우
            if request.path.startswith('/api/'):
                return JsonResponse({
                    'error': 'Service Unavailable',
                    'message': '시스템 점검 중입니다. 잠시 후 다시 시도해주세요.',
                    'maintenance': True
                }, status=503)
            
            # 일반 웹 요청인 경우 (PWA)
            from django.http import HttpResponse
            return HttpResponse(
                """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>OneSquare - 시스템 점검 중</title>
                    <meta charset="utf-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                </head>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h1>🔧 시스템 점검 중</h1>
                    <p>더 나은 서비스를 위해 시스템을 점검하고 있습니다.</p>
                    <p>잠시 후 다시 접속해주세요.</p>
                </body>
                </html>
                """,
                status=503
            )
        
        return None