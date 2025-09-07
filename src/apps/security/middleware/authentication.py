"""인증 강화 미들웨어"""
import logging
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import logout
from django.shortcuts import redirect
from datetime import datetime, timedelta

logger = logging.getLogger('apps.security')


class AuthenticationEnhancementMiddleware(MiddlewareMixin):
    """인증 보안 강화"""
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.session_timeout = getattr(settings, 'SESSION_TIMEOUT_MINUTES', 30)
        self.enforce_password_change = getattr(settings, 'ENFORCE_PASSWORD_CHANGE_DAYS', 90)
    
    def process_request(self, request):
        """인증 관련 보안 검사"""
        if not request.user.is_authenticated:
            return None
        
        # 세션 타임아웃 체크
        if self._is_session_expired(request):
            logout(request)
            return redirect('login')
        
        # 비밀번호 변경 주기 체크
        if self._needs_password_change(request.user):
            if request.path != '/accounts/password-change/':
                return redirect('password_change')
        
        # 세션 활동 시간 업데이트
        request.session['last_activity'] = datetime.now().isoformat()
        
        return None
    
    def _is_session_expired(self, request):
        """세션 만료 확인"""
        last_activity = request.session.get('last_activity')
        if not last_activity:
            return False
        
        last_activity_time = datetime.fromisoformat(last_activity)
        timeout_delta = timedelta(minutes=self.session_timeout)
        
        return datetime.now() - last_activity_time > timeout_delta
    
    def _needs_password_change(self, user):
        """비밀번호 변경 필요 여부 확인"""
        if not hasattr(user, 'profile'):
            return False
        
        last_password_change = getattr(user.profile, 'last_password_change', None)
        if not last_password_change:
            return True
        
        days_since_change = (datetime.now().date() - last_password_change).days
        return days_since_change >= self.enforce_password_change


class SessionSecurityMiddleware(MiddlewareMixin):
    """세션 보안 강화"""
    
    def process_request(self, request):
        """세션 보안 설정"""
        if request.user.is_authenticated:
            # 세션 고정 공격 방지
            if 'session_init' not in request.session:
                request.session.cycle_key()
                request.session['session_init'] = True
            
            # IP 주소 바인딩
            current_ip = self._get_client_ip(request)
            session_ip = request.session.get('session_ip')
            
            if not session_ip:
                request.session['session_ip'] = current_ip
            elif session_ip != current_ip:
                logger.warning(f"Session IP mismatch for user {request.user.username}")
                logout(request)
                return redirect('login')
        
        return None
    
    def _get_client_ip(self, request):
        """클라이언트 IP 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
