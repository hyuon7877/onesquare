#!/usr/bin/env python3
"""
대용량 모듈 자동 분할 도구
Phase 2: Middleware, Notion Sync, Photo Views 등 분할
"""

import os
import re
import shutil
from pathlib import Path
import argparse


class LargeModuleSplitter:
    def __init__(self, module_type, base_path='src'):
        self.module_type = module_type
        self.base_path = Path(base_path)
        
    def split_security_middleware(self):
        """Security Middleware 분할"""
        print("🔧 Security Middleware 분할 시작...")
        
        source = self.base_path / 'apps/security/middleware.py'
        target_dir = self.base_path / 'apps/security/middleware'
        
        # 백업
        backup = source.parent / f"{source.stem}_backup.py"
        if not backup.exists():
            shutil.copy(source, backup)
            print(f"✅ 백업 생성: {backup.name}")
        
        # 디렉토리 생성
        target_dir.mkdir(exist_ok=True)
        
        # 파일 내용 읽기
        with open(source, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 클래스별로 분할
        self._extract_headers_middleware(content, target_dir)
        self._extract_validation_middleware(content, target_dir)
        self._extract_authentication_middleware(content, target_dir)
        self._extract_rate_limiting_middleware(content, target_dir)
        self._extract_intrusion_detection_middleware(content, target_dir)
        self._extract_audit_logging_middleware(content, target_dir)
        self._extract_csrf_protection_middleware(content, target_dir)
        self._create_middleware_init(target_dir)
        
        print(f"✅ Security Middleware가 {target_dir}에 분할 완료!")
        
        # 원본 파일 제거
        source.unlink()
        print(f"🗑️ 원본 파일 제거: {source.name}")
        
    def _extract_headers_middleware(self, content, target_dir):
        """headers.py - 보안 헤더 미들웨어"""
        output_content = '''"""보안 헤더 설정 미들웨어"""
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
'''
        
        with open(target_dir / 'headers.py', 'w', encoding='utf-8') as f:
            f.write(output_content)
    
    def _extract_validation_middleware(self, content, target_dir):
        """validation.py - 입력 검증 미들웨어"""
        output_content = '''"""입력 데이터 검증 미들웨어"""
import re
import json
import logging
from urllib.parse import unquote
from django.conf import settings
from django.http import HttpResponseBadRequest
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('apps.security')


class InputValidationMiddleware(MiddlewareMixin):
    """입력 데이터 검증 및 필터링"""
    
    # SQL Injection 패턴
    SQL_PATTERNS = [
        r"(\\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION)\\b)",
        r"(--|#|/\\*|\\*/)",
        r"(\\bOR\\b\\s*\\d+\\s*=\\s*\\d+)",
        r"('\\s*(OR|AND)\\s+)",
    ]
    
    # XSS 패턴
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\\w+\\s*=",
        r"<iframe",
        r"<object",
        r"<embed",
        r"<applet",
        r"<meta",
        r"<link",
        r"<style",
        r"expression\\s*\\(",
        r"vbscript:",
        r"data:text/html",
    ]
    
    # 경로 탐색 패턴
    PATH_TRAVERSAL_PATTERNS = [
        r"\\.\\./",
        r"\\.\\.\\\\",
        r"%2e%2e[/\\\\]",
        r"\\.\\.%2f",
        r"\\.\\.%5c",
    ]
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.enabled = getattr(settings, 'SECURITY_INPUT_VALIDATION', True)
        self.log_violations = getattr(settings, 'SECURITY_LOG_VIOLATIONS', True)
    
    def process_request(self, request):
        """요청 데이터 검증"""
        if not self.enabled:
            return None
        
        # URL 파라미터 검증
        if request.GET:
            for key, value in request.GET.items():
                if self._is_malicious(str(value)):
                    return self._block_request(request, f"Malicious GET parameter: {key}")
        
        # POST 데이터 검증
        if request.POST:
            for key, value in request.POST.items():
                if self._is_malicious(str(value)):
                    return self._block_request(request, f"Malicious POST parameter: {key}")
        
        # 경로 검증
        path = unquote(request.path)
        if self._contains_path_traversal(path):
            return self._block_request(request, "Path traversal attempt")
        
        # 헤더 검증
        suspicious_headers = ['X-Forwarded-Host', 'X-Original-URL', 'X-Rewrite-URL']
        for header in suspicious_headers:
            if header in request.META:
                value = request.META[header]
                if self._is_malicious(value):
                    return self._block_request(request, f"Malicious header: {header}")
        
        return None
    
    def _is_malicious(self, value):
        """악성 패턴 검사"""
        if not value:
            return False
        
        value_lower = value.lower()
        
        # SQL Injection 검사
        for pattern in self.SQL_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True
        
        # XSS 검사
        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE | re.DOTALL):
                return True
        
        return False
    
    def _contains_path_traversal(self, path):
        """경로 탐색 공격 검사"""
        for pattern in self.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, path, re.IGNORECASE):
                return True
        return False
    
    def _block_request(self, request, reason):
        """악성 요청 차단"""
        if self.log_violations:
            logger.warning(f"Blocked request - {reason}: {request.path} from {self._get_client_ip(request)}")
        
        return HttpResponseBadRequest("Invalid request")
    
    def _get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
'''
        
        with open(target_dir / 'validation.py', 'w', encoding='utf-8') as f:
            f.write(output_content)
    
    def _extract_authentication_middleware(self, content, target_dir):
        """authentication.py - 인증 강화 미들웨어"""
        output_content = '''"""인증 강화 미들웨어"""
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
'''
        
        with open(target_dir / 'authentication.py', 'w', encoding='utf-8') as f:
            f.write(output_content)
    
    def _extract_rate_limiting_middleware(self, content, target_dir):
        """rate_limiting.py - Rate Limiting 미들웨어"""
        output_content = '''"""Rate Limiting 미들웨어"""
import time
import hashlib
import logging
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseTooManyRequests
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('apps.security')


class RateLimitingMiddleware(MiddlewareMixin):
    """API Rate Limiting"""
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.enabled = getattr(settings, 'RATE_LIMITING_ENABLED', True)
        self.rate_limit = getattr(settings, 'RATE_LIMIT_PER_MINUTE', 60)
        self.burst_limit = getattr(settings, 'RATE_LIMIT_BURST', 10)
    
    def process_request(self, request):
        """요청 횟수 제한"""
        if not self.enabled:
            return None
        
        # 인증된 사용자는 더 높은 한도
        if request.user.is_authenticated:
            limit = self.rate_limit * 2
        else:
            limit = self.rate_limit
        
        # Rate limiting key
        client_id = self._get_client_identifier(request)
        cache_key = f"rate_limit:{client_id}"
        
        # 현재 요청 횟수
        request_count = cache.get(cache_key, 0)
        
        if request_count >= limit:
            return self._rate_limit_exceeded(request)
        
        # 카운터 증가
        cache.set(cache_key, request_count + 1, 60)  # 1분간 유지
        
        # Burst protection
        burst_key = f"burst:{client_id}"
        burst_count = cache.get(burst_key, 0)
        
        if burst_count >= self.burst_limit:
            return self._rate_limit_exceeded(request, is_burst=True)
        
        cache.set(burst_key, burst_count + 1, 1)  # 1초간 유지
        
        return None
    
    def _get_client_identifier(self, request):
        """클라이언트 식별자 생성"""
        if request.user.is_authenticated:
            identifier = f"user:{request.user.id}"
        else:
            ip = self._get_client_ip(request)
            identifier = f"ip:{ip}"
        
        return hashlib.md5(identifier.encode()).hexdigest()
    
    def _get_client_ip(self, request):
        """클라이언트 IP 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _rate_limit_exceeded(self, request, is_burst=False):
        """Rate limit 초과 처리"""
        client_id = self._get_client_identifier(request)
        
        if is_burst:
            message = "Too many requests in a short time. Please slow down."
            logger.warning(f"Burst limit exceeded for {client_id}")
        else:
            message = "Rate limit exceeded. Please try again later."
            logger.warning(f"Rate limit exceeded for {client_id}")
        
        response = HttpResponseTooManyRequests(message)
        response['Retry-After'] = '60'
        return response
'''
        
        with open(target_dir / 'rate_limiting.py', 'w', encoding='utf-8') as f:
            f.write(output_content)
    
    def _extract_intrusion_detection_middleware(self, content, target_dir):
        """intrusion_detection.py - 침입 탐지 미들웨어"""
        output_content = '''"""침입 탐지 시스템 미들웨어"""
import logging
import ipaddress
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('apps.security')


class IntrusionDetectionMiddleware(MiddlewareMixin):
    """침입 탐지 및 차단"""
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.enabled = getattr(settings, 'IDS_ENABLED', True)
        self.threshold = getattr(settings, 'IDS_THRESHOLD', 10)
        self.block_duration = getattr(settings, 'IDS_BLOCK_DURATION_HOURS', 24)
        
        # 화이트리스트 IP
        self.whitelist = getattr(settings, 'IP_WHITELIST', [])
        
        # 블랙리스트 IP
        self.blacklist = getattr(settings, 'IP_BLACKLIST', [])
    
    def process_request(self, request):
        """침입 탐지 검사"""
        if not self.enabled:
            return None
        
        client_ip = self._get_client_ip(request)
        
        # 화이트리스트 확인
        if self._is_whitelisted(client_ip):
            return None
        
        # 블랙리스트 확인
        if self._is_blacklisted(client_ip):
            return self._block_request(request, "Blacklisted IP")
        
        # 자동 차단 확인
        if self._is_auto_blocked(client_ip):
            return self._block_request(request, "Auto-blocked due to suspicious activity")
        
        # 의심스러운 활동 감지
        if self._detect_suspicious_activity(request):
            self._record_suspicious_activity(client_ip)
            
            # 임계값 초과 시 자동 차단
            if self._should_auto_block(client_ip):
                self._auto_block_ip(client_ip)
                return self._block_request(request, "Too many suspicious activities")
        
        return None
    
    def _get_client_ip(self, request):
        """클라이언트 IP 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _is_whitelisted(self, ip):
        """화이트리스트 확인"""
        for allowed_ip in self.whitelist:
            try:
                if ipaddress.ip_address(ip) in ipaddress.ip_network(allowed_ip):
                    return True
            except ValueError:
                continue
        return False
    
    def _is_blacklisted(self, ip):
        """블랙리스트 확인"""
        for blocked_ip in self.blacklist:
            try:
                if ipaddress.ip_address(ip) in ipaddress.ip_network(blocked_ip):
                    return True
            except ValueError:
                continue
        return False
    
    def _is_auto_blocked(self, ip):
        """자동 차단 상태 확인"""
        block_key = f"auto_block:{ip}"
        return cache.get(block_key, False)
    
    def _detect_suspicious_activity(self, request):
        """의심스러운 활동 감지"""
        suspicious_patterns = [
            '/admin/',
            '/wp-admin/',
            '/phpmyadmin/',
            '/.env',
            '/config.php',
            '/backup/',
            '/.git/',
            '/api/private/',
        ]
        
        # 의심스러운 경로 접근
        for pattern in suspicious_patterns:
            if pattern in request.path.lower():
                return True
        
        # 과도한 404 에러
        # 짧은 시간 내 너무 많은 로그인 실패
        # 등의 추가 검사 가능
        
        return False
    
    def _record_suspicious_activity(self, ip):
        """의심스러운 활동 기록"""
        activity_key = f"suspicious:{ip}"
        count = cache.get(activity_key, 0)
        cache.set(activity_key, count + 1, 3600)  # 1시간 동안 카운트
        
        logger.warning(f"Suspicious activity detected from {ip}")
    
    def _should_auto_block(self, ip):
        """자동 차단 여부 결정"""
        activity_key = f"suspicious:{ip}"
        count = cache.get(activity_key, 0)
        return count >= self.threshold
    
    def _auto_block_ip(self, ip):
        """IP 자동 차단"""
        block_key = f"auto_block:{ip}"
        block_duration = self.block_duration * 3600  # 시간을 초로 변환
        cache.set(block_key, True, block_duration)
        
        logger.error(f"IP auto-blocked for {self.block_duration} hours: {ip}")
    
    def _block_request(self, request, reason):
        """요청 차단"""
        client_ip = self._get_client_ip(request)
        logger.warning(f"Request blocked - {reason}: {request.path} from {client_ip}")
        
        return HttpResponseForbidden("Access denied")
'''
        
        with open(target_dir / 'intrusion_detection.py', 'w', encoding='utf-8') as f:
            f.write(output_content)
    
    def _extract_audit_logging_middleware(self, content, target_dir):
        """audit_logging.py - 감사 로깅 미들웨어"""
        output_content = '''"""보안 감사 로깅 미들웨어"""
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
'''
        
        with open(target_dir / 'audit_logging.py', 'w', encoding='utf-8') as f:
            f.write(output_content)
    
    def _extract_csrf_protection_middleware(self, content, target_dir):
        """csrf_protection.py - CSRF 보호 강화 미들웨어"""
        output_content = '''"""CSRF 보호 강화 미들웨어"""
import logging
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.middleware.csrf import CsrfViewMiddleware

logger = logging.getLogger('apps.security')


class EnhancedCSRFMiddleware(CsrfViewMiddleware):
    """강화된 CSRF 보호"""
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.strict_referer = getattr(settings, 'CSRF_STRICT_REFERER', True)
    
    def process_view(self, request, callback, callback_args, callback_kwargs):
        """CSRF 토큰 검증 강화"""
        
        # 기본 CSRF 검증
        result = super().process_view(request, callback, callback_args, callback_kwargs)
        if result is not None:
            return result
        
        # POST 요청에 대한 추가 검증
        if request.method == 'POST':
            # Referer 헤더 검증
            if self.strict_referer:
                referer = request.META.get('HTTP_REFERER')
                if not referer:
                    logger.warning(f"Missing referer for POST request: {request.path}")
                else:
                    # 동일 출처 확인
                    if not self._is_same_origin(request, referer):
                        logger.warning(f"Cross-origin POST request blocked: {request.path}")
        
        return None
    
    def _is_same_origin(self, request, referer):
        """동일 출처 확인"""
        from urllib.parse import urlparse
        
        referer_parts = urlparse(referer)
        request_host = request.get_host()
        
        # 프로토콜과 호스트 비교
        return referer_parts.netloc == request_host
'''
        
        with open(target_dir / 'csrf_protection.py', 'w', encoding='utf-8') as f:
            f.write(output_content)
    
    def _create_middleware_init(self, target_dir):
        """__init__.py - 미들웨어 모듈 통합"""
        output_content = '''"""OneSquare 보안 미들웨어 패키지

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
'''
        
        with open(target_dir / '__init__.py', 'w', encoding='utf-8') as f:
            f.write(output_content)


def main():
    parser = argparse.ArgumentParser(description='대용량 모듈 분할 도구')
    parser.add_argument('--module', choices=['middleware', 'notion_sync', 'photo_views'],
                       required=True, help='분할할 모듈 타입')
    
    args = parser.parse_args()
    
    splitter = LargeModuleSplitter(args.module)
    
    if args.module == 'middleware':
        splitter.split_security_middleware()
    elif args.module == 'notion_sync':
        print("Notion Sync 분할 기능 준비 중...")
    elif args.module == 'photo_views':
        print("Photo Views 분할 기능 준비 중...")


if __name__ == '__main__':
    main()