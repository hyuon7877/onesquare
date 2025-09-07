"""보안 감사 로깅 미들웨어"""
import json
import logging
from datetime import datetime
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('apps.security.audit')


class AuditLoggingMiddleware(MiddlewareMixin):
    """보안 감사 로깅"""
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.enabled = getattr(settings, 'AUDIT_LOGGING_ENABLED', True)
        self.sensitive_paths = getattr(settings, 'AUDIT_SENSITIVE_PATHS', [
            '/admin/',
            '/api/auth/',
            '/accounts/',
        ])
    
    def process_request(self, request):
        """요청 로깅"""
        if not self.enabled:
            return None
        
        # 민감한 경로 접근 로깅
        if any(request.path.startswith(path) for path in self.sensitive_paths):
            self._log_sensitive_access(request)
        
        # 요청 시작 시간 저장
        request._audit_start_time = datetime.now()
        
        return None
    
    def process_response(self, request, response):
        """응답 로깅"""
        if not self.enabled:
            return response
        
        # 처리 시간 계산
        if hasattr(request, '_audit_start_time'):
            duration = (datetime.now() - request._audit_start_time).total_seconds()
        else:
            duration = 0
        
        # 감사 로그 생성
        audit_log = self._create_audit_log(request, response, duration)
        
        # 로그 기록
        if response.status_code >= 400:
            logger.warning(json.dumps(audit_log))
        elif any(request.path.startswith(path) for path in self.sensitive_paths):
            logger.info(json.dumps(audit_log))
        
        return response
    
    def _log_sensitive_access(self, request):
        """민감한 경로 접근 로깅"""
        log_data = {
            'event': 'sensitive_access',
            'timestamp': datetime.now().isoformat(),
            'user': request.user.username if request.user.is_authenticated else 'anonymous',
            'ip': self._get_client_ip(request),
            'path': request.path,
            'method': request.method,
        }
        
        logger.info(json.dumps(log_data))
    
    def _create_audit_log(self, request, response, duration):
        """감사 로그 생성"""
        return {
            'timestamp': datetime.now().isoformat(),
            'user': request.user.username if request.user.is_authenticated else 'anonymous',
            'ip': self._get_client_ip(request),
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'duration_seconds': round(duration, 3),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        }
    
    def _get_client_ip(self, request):
        """클라이언트 IP 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
