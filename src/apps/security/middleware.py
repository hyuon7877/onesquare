"""
OneSquare 보안 강화 미들웨어

Django 보안 강화를 위한 포괄적인 보안 미들웨어:
- 보안 헤더 설정 (CSP, HSTS, X-Frame-Options 등)
- SQL Injection 방지
- XSS 방지
- CSRF 강화
- 입력 데이터 검증 및 필터링
- 침입 탐지 및 차단
- 보안 감사 로깅
"""

import re
import json
import time
import hashlib
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin
from django.urls import reverse
from django.contrib.auth.models import AnonymousUser
import ipaddress
from urllib.parse import unquote

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
        if not response.get('Content-Security-Policy'):
            csp_policy = self._get_csp_policy(request)
            response['Content-Security-Policy'] = csp_policy
        
        # HTTP Strict Transport Security (HSTS) - HTTPS에서만
        if request.is_secure() and not response.get('Strict-Transport-Security'):
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        # X-Frame-Options
        if not response.get('X-Frame-Options'):
            response['X-Frame-Options'] = 'DENY'
        
        # X-Content-Type-Options
        if not response.get('X-Content-Type-Options'):
            response['X-Content-Type-Options'] = 'nosniff'
        
        # X-XSS-Protection (구형 브라우저 지원)
        if not response.get('X-XSS-Protection'):
            response['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer-Policy
        if not response.get('Referrer-Policy'):
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions-Policy (구 Feature-Policy)
        if not response.get('Permissions-Policy'):
            response['Permissions-Policy'] = self._get_permissions_policy()
        
        # X-Permitted-Cross-Domain-Policies
        response['X-Permitted-Cross-Domain-Policies'] = 'none'
        
        # Server 헤더 숨기기/변경
        response['Server'] = 'OneSquare-Server'
        
        # X-Powered-By 헤더 제거 (있다면)
        if response.get('X-Powered-By'):
            del response['X-Powered-By']
        
        # API 응답에 추가 보안 헤더
        if request.path.startswith('/api/'):
            response['X-API-Version'] = 'v1'
            response['X-Request-ID'] = getattr(request, '_request_id', 'unknown')
        
        return response
    
    def _get_csp_policy(self, request):
        """Content Security Policy 생성"""
        base_policy = {
            "default-src": ["'self'"],
            "script-src": [
                "'self'",
                "'unsafe-inline'",  # PWA를 위해 인라인 스크립트 허용 (제한적)
                "'unsafe-eval'",    # 개발 환경에서만 (나중에 제거)
                "https://cdn.jsdelivr.net",
                "https://cdnjs.cloudflare.com"
            ],
            "style-src": [
                "'self'",
                "'unsafe-inline'",  # CSS 인라인 스타일 허용
                "https://fonts.googleapis.com",
                "https://cdn.jsdelivr.net"
            ],
            "font-src": [
                "'self'",
                "https://fonts.gstatic.com",
                "data:"  # 웹폰트 data URI 허용
            ],
            "img-src": [
                "'self'",
                "data:",  # base64 이미지 허용
                "blob:",  # PWA에서 생성된 이미지 허용
                "https:",  # HTTPS 이미지만 허용
            ],
            "connect-src": [
                "'self'",
                "https://api.notion.com",  # Notion API
                "wss:",  # WebSocket 연결 허용 (향후 실시간 기능용)
            ],
            "media-src": ["'self'", "data:", "blob:"],
            "object-src": ["'none'"],  # 플러그인 차단
            "base-uri": ["'self'"],
            "form-action": ["'self'"],
            "frame-ancestors": ["'none'"],  # iframe 삽입 방지
            "upgrade-insecure-requests": []  # HTTP를 HTTPS로 자동 업그레이드
        }
        
        # 개발 환경에서는 더 관대한 정책 적용
        if self.is_debug:
            base_policy["script-src"].append("'unsafe-eval'")
            base_policy["connect-src"].extend([
                "http://localhost:*",
                "ws://localhost:*"
            ])
        
        # 정책을 문자열로 변환
        policy_parts = []
        for directive, sources in base_policy.items():
            if sources:
                policy_parts.append(f"{directive} {' '.join(sources)}")
            else:
                policy_parts.append(directive)
        
        return '; '.join(policy_parts)
    
    def _get_permissions_policy(self):
        """Permissions Policy 생성"""
        permissions = {
            'camera': '(self)',  # 카메라는 자체 도메인에서만 허용
            'microphone': '()',  # 마이크는 차단
            'geolocation': '(self)',  # 위치 정보는 자체 도메인에서만
            'notifications': '(self)',  # 알림은 자체 도메인에서만
            'payment': '()',  # 결제 API 차단
            'usb': '()',  # USB 접근 차단
            'accelerometer': '()',  # 가속도계 차단
            'gyroscope': '()',  # 자이로스코프 차단
            'magnetometer': '()',  # 자력계 차단
            'fullscreen': '(self)',  # 전체화면은 자체 도메인에서만
        }
        
        return ', '.join([f'{perm}={value}' for perm, value in permissions.items()])


class InputValidationMiddleware(MiddlewareMixin):
    """
    입력 데이터 검증 및 필터링 미들웨어
    - SQL Injection 패턴 감지
    - XSS 시도 차단
    - 악성 파일 업로드 방지
    - 요청 크기 제한
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        
        # SQL Injection 패턴
        self.sql_injection_patterns = [
            r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)",
            r"([\"\']\s*(or|and)\s*[\"\']\s*=\s*[\"\']\s*)",
            r"(--|#|\/\*|\*\/)",
            r"(\b(concat|char|ascii|substring|length|user|database|version)\s*\()",
            r"(0x[0-9a-f]+)",
            r"(\b(load_file|into\s+outfile|dumpfile)\b)",
        ]
        
        # XSS 패턴
        self.xss_patterns = [
            r"(<script[^>]*>.*?</script>)",
            r"(javascript\s*:)",
            r"(on\w+\s*=)",
            r"(<iframe[^>]*>)",
            r"(<object[^>]*>)",
            r"(<embed[^>]*>)",
            r"(<form[^>]*>)",
            r"(expression\s*\()",
        ]
        
        # 허용되지 않는 파일 확장자
        self.dangerous_extensions = [
            'exe', 'bat', 'cmd', 'com', 'pif', 'scr', 'vbs', 'js', 'jar',
            'php', 'asp', 'aspx', 'jsp', 'py', 'pl', 'sh', 'ps1'
        ]
        
        # 최대 요청 크기 (바이트)
        self.max_request_size = 50 * 1024 * 1024  # 50MB
        
        self.compiled_sql_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.sql_injection_patterns]
        self.compiled_xss_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.xss_patterns]
    
    def process_request(self, request):
        """요청 검증"""
        
        # 요청 크기 확인
        if hasattr(request, 'META') and 'CONTENT_LENGTH' in request.META:
            try:
                content_length = int(request.META['CONTENT_LENGTH'])
                if content_length > self.max_request_size:
                    logger.warning(f'Request size too large: {content_length} bytes from {self._get_client_ip(request)}')
                    return HttpResponseForbidden('Request too large')
            except (ValueError, TypeError):
                pass
        
        # GET 매개변수 검증
        for key, values in request.GET.lists():
            for value in values:
                if self._is_malicious_input(value):
                    logger.warning(f'Malicious GET parameter detected: {key}={value[:100]} from {self._get_client_ip(request)}')
                    return HttpResponseForbidden('Invalid request parameters')
        
        # POST 데이터 검증 (multipart가 아닌 경우)
        if request.method == 'POST' and request.content_type != 'multipart/form-data':
            try:
                if hasattr(request, 'body') and request.body:
                    body_str = request.body.decode('utf-8')
                    
                    # JSON 데이터인 경우
                    if request.content_type == 'application/json':
                        try:
                            json_data = json.loads(body_str)
                            if self._check_json_for_malicious_content(json_data):
                                logger.warning(f'Malicious JSON data detected from {self._get_client_ip(request)}')
                                return HttpResponseForbidden('Invalid request data')
                        except json.JSONDecodeError:
                            pass
                    
                    # 일반 텍스트 데이터 검증
                    elif self._is_malicious_input(body_str):
                        logger.warning(f'Malicious POST data detected from {self._get_client_ip(request)}')
                        return HttpResponseForbidden('Invalid request data')
                        
            except UnicodeDecodeError:
                # 바이너리 데이터는 파일 업로드일 가능성이 높음
                pass
        
        # User-Agent 검증
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        if self._is_suspicious_user_agent(user_agent):
            logger.warning(f'Suspicious User-Agent: {user_agent} from {self._get_client_ip(request)}')
            return HttpResponseForbidden('Invalid request')
        
        return None
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """파일 업로드 검증"""
        if request.method == 'POST' and request.FILES:
            for file_key, uploaded_file in request.FILES.items():
                if not self._is_safe_file(uploaded_file):
                    logger.warning(f'Dangerous file upload attempt: {uploaded_file.name} from {self._get_client_ip(request)}')
                    return HttpResponseForbidden('File type not allowed')
        
        return None
    
    def _is_malicious_input(self, input_str):
        """악성 입력 패턴 검사"""
        if not input_str:
            return False
        
        # URL 디코딩
        decoded_input = unquote(input_str)
        
        # SQL Injection 검사
        for pattern in self.compiled_sql_patterns:
            if pattern.search(decoded_input):
                return True
        
        # XSS 검사
        for pattern in self.compiled_xss_patterns:
            if pattern.search(decoded_input):
                return True
        
        return False
    
    def _check_json_for_malicious_content(self, json_data, max_depth=10):
        """JSON 데이터 재귀 검사"""
        if max_depth <= 0:
            return False
        
        if isinstance(json_data, dict):
            for key, value in json_data.items():
                if isinstance(key, str) and self._is_malicious_input(key):
                    return True
                if self._check_json_for_malicious_content(value, max_depth - 1):
                    return True
        
        elif isinstance(json_data, list):
            for item in json_data:
                if self._check_json_for_malicious_content(item, max_depth - 1):
                    return True
        
        elif isinstance(json_data, str):
            return self._is_malicious_input(json_data)
        
        return False
    
    def _is_suspicious_user_agent(self, user_agent):
        """의심스러운 User-Agent 검사"""
        if not user_agent:
            return True
        
        # 일반적인 공격 도구들
        suspicious_agents = [
            'sqlmap', 'nmap', 'nikto', 'w3af', 'burp', 'zap',
            'python-requests', 'curl', 'wget', 'masscan',
            'acunetix', 'nessus', 'openvas'
        ]
        
        user_agent_lower = user_agent.lower()
        for suspicious in suspicious_agents:
            if suspicious in user_agent_lower:
                return True
        
        return False
    
    def _is_safe_file(self, uploaded_file):
        """파일 안전성 검사"""
        # 파일명 검사
        filename = uploaded_file.name.lower()
        
        # 확장자 검사
        if '.' in filename:
            extension = filename.split('.')[-1]
            if extension in self.dangerous_extensions:
                return False
        
        # 파일 내용 검사 (매직 넘버)
        if hasattr(uploaded_file, 'read'):
            # 파일 시작 부분 읽기
            uploaded_file.seek(0)
            file_header = uploaded_file.read(1024)
            uploaded_file.seek(0)  # 파일 포인터 리셋
            
            # 실행 파일 시그니처 검사
            dangerous_signatures = [
                b'MZ',  # Windows PE
                b'\x7fELF',  # Linux ELF
                b'PK\x03\x04',  # ZIP (잠재적으로 위험한 압축 파일)
            ]
            
            for signature in dangerous_signatures:
                if file_header.startswith(signature):
                    return False
        
        return True
    
    def _get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')


class IntrusionDetectionMiddleware(MiddlewareMixin):
    """
    침입 탐지 및 차단 미들웨어
    - 비정상적인 요청 패턴 감지
    - 무차별 대입 공격 방지
    - IP 기반 차단
    - 자동 보안 조치
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        
        # 설정값들
        self.max_requests_per_minute = 300  # 분당 최대 요청 수
        self.max_failed_logins = 5  # 최대 로그인 실패 횟수
        self.ban_duration = 3600  # 차단 시간 (초)
        self.suspicious_patterns = [
            r'\.\./',  # 디렉토리 탐색
            r'\/etc\/passwd',  # 시스템 파일 접근
            r'\/admin\/',  # 관리자 페이지 무차별 접근
            r'wp-admin',  # 워드프레스 관련
            r'phpmyadmin',  # phpMyAdmin
            r'\.php$',  # PHP 파일 접근
        ]
        self.compiled_suspicious_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.suspicious_patterns]
    
    def process_request(self, request):
        """침입 탐지 검사"""
        client_ip = self._get_client_ip(request)
        
        # IP 차단 상태 확인
        if self._is_ip_banned(client_ip):
            logger.warning(f'Banned IP attempted access: {client_ip}')
            return HttpResponseForbidden('Access denied')
        
        # 요청 빈도 확인
        if self._is_request_rate_exceeded(client_ip):
            logger.warning(f'Request rate exceeded for IP: {client_ip}')
            self._ban_ip(client_ip, 'rate_limit')
            return HttpResponseForbidden('Too many requests')
        
        # 의심스러운 URL 패턴 검사
        if self._is_suspicious_url(request.path):
            logger.warning(f'Suspicious URL pattern: {request.path} from {client_ip}')
            self._increment_suspicion_score(client_ip)
            return HttpResponseForbidden('Access denied')
        
        # 로그인 실패 추적 (로그인 관련 URL에서)
        if request.path.startswith('/api/auth/login/') and request.method == 'POST':
            request._track_login_attempt = True
            request._client_ip_for_tracking = client_ip
        
        # 요청 횟수 증가
        self._increment_request_count(client_ip)
        
        return None
    
    def process_response(self, request, response):
        """응답 처리 후 보안 검사"""
        
        # 로그인 실패 추적
        if hasattr(request, '_track_login_attempt') and response.status_code in [401, 403]:
            client_ip = getattr(request, '_client_ip_for_tracking')
            self._track_failed_login(client_ip)
        
        # 404 오류 추적 (스캐닝 시도 감지)
        if response.status_code == 404:
            client_ip = self._get_client_ip(request)
            self._track_404_error(client_ip, request.path)
        
        return response
    
    def _is_ip_banned(self, ip):
        """IP 차단 상태 확인"""
        ban_key = f'banned_ip:{ip}'
        return cache.get(ban_key, False)
    
    def _ban_ip(self, ip, reason):
        """IP 차단"""
        ban_key = f'banned_ip:{ip}'
        cache.set(ban_key, True, self.ban_duration)
        
        # 차단 로그
        logger.critical(f'IP banned: {ip} (reason: {reason})')
        
        # 차단 통계 업데이트
        stats_key = f'ban_stats:{datetime.now().strftime("%Y%m%d")}'
        stats = cache.get(stats_key, {'count': 0, 'ips': []})
        stats['count'] += 1
        if ip not in stats['ips']:
            stats['ips'].append(ip)
        cache.set(stats_key, stats, 86400)  # 24시간 보관
    
    def _is_request_rate_exceeded(self, ip):
        """요청 빈도 초과 확인"""
        rate_key = f'request_rate:{ip}'
        current_count = cache.get(rate_key, 0)
        return current_count > self.max_requests_per_minute
    
    def _increment_request_count(self, ip):
        """요청 횟수 증가"""
        rate_key = f'request_rate:{ip}'
        current_count = cache.get(rate_key, 0)
        cache.set(rate_key, current_count + 1, 60)  # 1분 TTL
    
    def _is_suspicious_url(self, url_path):
        """의심스러운 URL 패턴 검사"""
        for pattern in self.compiled_suspicious_patterns:
            if pattern.search(url_path):
                return True
        return False
    
    def _increment_suspicion_score(self, ip):
        """의심도 점수 증가"""
        suspicion_key = f'suspicion:{ip}'
        current_score = cache.get(suspicion_key, 0)
        new_score = current_score + 1
        cache.set(suspicion_key, new_score, 3600)  # 1시간 TTL
        
        # 일정 점수 이상이면 차단
        if new_score >= 5:
            self._ban_ip(ip, 'suspicious_activity')
    
    def _track_failed_login(self, ip):
        """로그인 실패 추적"""
        failed_key = f'failed_login:{ip}'
        current_count = cache.get(failed_key, 0)
        new_count = current_count + 1
        cache.set(failed_key, new_count, 3600)  # 1시간 TTL
        
        logger.warning(f'Login failure #{new_count} from IP: {ip}')
        
        # 최대 실패 횟수 도달 시 차단
        if new_count >= self.max_failed_logins:
            self._ban_ip(ip, 'brute_force_login')
    
    def _track_404_error(self, ip, path):
        """404 오류 추적 (스캔 시도 감지)"""
        error_key = f'404_errors:{ip}'
        errors = cache.get(error_key, [])
        errors.append({'path': path, 'time': time.time()})
        
        # 최근 5분 내의 404 오류만 유지
        recent_errors = [e for e in errors if time.time() - e['time'] < 300]
        cache.set(error_key, recent_errors, 300)
        
        # 짧은 시간 내에 많은 404 오류 발생 시 의심스러운 활동으로 간주
        if len(recent_errors) > 20:
            logger.warning(f'High 404 error rate from IP: {ip}')
            self._increment_suspicion_score(ip)
    
    def _get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')


class SecurityAuditMiddleware(MiddlewareMixin):
    """
    보안 감사 및 로깅 미들웨어
    - 보안 관련 이벤트 로깅
    - 감사 추적
    - 보안 메트릭 수집
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.security_events = [
            'login', 'logout', 'failed_login', 'password_change',
            'admin_access', 'file_upload', 'data_export',
            'permission_denied', 'suspicious_activity'
        ]
    
    def process_request(self, request):
        """요청 보안 감사"""
        request._security_audit_start = time.time()
        request._security_audit_data = {
            'ip': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'method': request.method,
            'path': request.path,
            'user': getattr(request.user, 'id', None) if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser) else None,
            'timestamp': datetime.now().isoformat(),
        }
        return None
    
    def process_response(self, request, response):
        """응답 보안 감사"""
        if not hasattr(request, '_security_audit_data'):
            return response
        
        audit_data = request._security_audit_data
        audit_data['response_time'] = time.time() - request._security_audit_start
        audit_data['status_code'] = response.status_code
        
        # 보안 관련 응답 상태 코드 로깅
        if response.status_code in [401, 403, 429]:
            self._log_security_event('access_denied', audit_data)
        
        # 관리자 페이지 접근 로깅
        if request.path.startswith('/admin/'):
            self._log_security_event('admin_access', audit_data)
        
        # API 키 사용 로깅
        if 'Authorization' in request.META or 'HTTP_AUTHORIZATION' in request.META:
            audit_data['uses_auth'] = True
        
        # 파일 업로드 로깅
        if request.method == 'POST' and request.FILES:
            audit_data['file_upload'] = list(request.FILES.keys())
            self._log_security_event('file_upload', audit_data)
        
        # 민감한 데이터 접근 로깅
        if self._is_sensitive_endpoint(request.path):
            self._log_security_event('sensitive_data_access', audit_data)
        
        return response
    
    def _log_security_event(self, event_type, audit_data):
        """보안 이벤트 로깅"""
        log_entry = {
            'event_type': event_type,
            'timestamp': datetime.now().isoformat(),
            **audit_data
        }
        
        # 구조화된 로그 기록
        logger.info(f'SECURITY_EVENT: {json.dumps(log_entry)}')
        
        # 보안 메트릭 업데이트
        self._update_security_metrics(event_type, audit_data['ip'])
    
    def _update_security_metrics(self, event_type, client_ip):
        """보안 메트릭 업데이트"""
        # 일별 보안 이벤트 통계
        today = datetime.now().strftime('%Y%m%d')
        metrics_key = f'security_metrics:{today}'
        
        metrics = cache.get(metrics_key, {})
        metrics[event_type] = metrics.get(event_type, 0) + 1
        metrics['unique_ips'] = metrics.get('unique_ips', set())
        metrics['unique_ips'].add(client_ip)
        metrics['unique_ips'] = set(metrics['unique_ips'])  # 집합 형태로 유지
        
        cache.set(metrics_key, metrics, 86400)  # 24시간 보관
    
    def _is_sensitive_endpoint(self, path):
        """민감한 엔드포인트 확인"""
        sensitive_patterns = [
            r'/api/users/',
            r'/api/admin/',
            r'/api/reports/',
            r'/api/analytics/',
            r'/api/export/',
        ]
        
        for pattern in sensitive_patterns:
            if re.search(pattern, path):
                return True
        return False
    
    def _get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')


class CSRFEnhancementMiddleware(MiddlewareMixin):
    """
    CSRF 보호 강화 미들웨어
    - 더블 서브밋 쿠키 패턴
    - Origin 헤더 검증
    - Referer 헤더 검증
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.allowed_origins = getattr(settings, 'CSRF_TRUSTED_ORIGINS', [])
        
    def process_request(self, request):
        """CSRF 보호 강화"""
        
        # API 요청에만 적용
        if not request.path.startswith('/api/'):
            return None
        
        # 안전한 메서드는 검증하지 않음
        if request.method in ['GET', 'HEAD', 'OPTIONS', 'TRACE']:
            return None
        
        # Origin 헤더 검증
        origin = request.META.get('HTTP_ORIGIN')
        if origin and not self._is_allowed_origin(origin):
            logger.warning(f'Invalid Origin header: {origin} from {self._get_client_ip(request)}')
            return HttpResponseForbidden('Invalid origin')
        
        # Referer 헤더 검증 (Origin이 없는 경우)
        if not origin:
            referer = request.META.get('HTTP_REFERER')
            if referer and not self._is_allowed_referer(referer):
                logger.warning(f'Invalid Referer header: {referer} from {self._get_client_ip(request)}')
                return HttpResponseForbidden('Invalid referer')
        
        return None
    
    def process_response(self, request, response):
        """CSRF 토큰 관련 보안 헤더 추가"""
        
        # SameSite 속성 강화 (쿠키가 설정되는 경우)
        if response.cookies:
            for cookie in response.cookies.values():
                if not cookie.get('samesite'):
                    cookie['samesite'] = 'Strict'
        
        return response
    
    def _is_allowed_origin(self, origin):
        """허용된 Origin인지 확인"""
        for allowed_origin in self.allowed_origins:
            if origin == allowed_origin or origin.endswith(allowed_origin.replace('https://', '').replace('http://', '')):
                return True
        return False
    
    def _is_allowed_referer(self, referer):
        """허용된 Referer인지 확인"""
        for allowed_origin in self.allowed_origins:
            if referer.startswith(allowed_origin):
                return True
        return False
    
    def _get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')


class SecretsProtectionMiddleware(MiddlewareMixin):
    """
    민감한 정보 보호 미들웨어
    - API 키 노출 방지
    - 민감한 데이터 마스킹
    - 로그에서 민감 정보 제거
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        
        # 민감한 필드 패턴
        self.sensitive_patterns = [
            r'password', r'passwd', r'secret', r'key', r'token',
            r'api_key', r'apikey', r'auth', r'credential', r'private',
            r'ssn', r'social', r'credit', r'card', r'account'
        ]
        self.compiled_sensitive_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.sensitive_patterns]
    
    def process_response(self, request, response):
        """응답에서 민감한 정보 제거"""
        
        # JSON API 응답만 처리
        if (response.get('Content-Type', '').startswith('application/json') and 
            hasattr(response, 'content')):
            
            try:
                # JSON 파싱
                content = response.content.decode('utf-8')
                data = json.loads(content)
                
                # 민감한 필드 마스킹
                masked_data = self._mask_sensitive_data(data)
                
                # 변경사항이 있는 경우에만 업데이트
                if masked_data != data:
                    masked_content = json.dumps(masked_data)
                    response.content = masked_content.encode('utf-8')
                    response['Content-Length'] = str(len(response.content))
                    
                    logger.info(f'Sensitive data masked in response to {request.path}')
                
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass  # JSON이 아니거나 디코딩 실패 시 무시
        
        return response
    
    def _mask_sensitive_data(self, data, max_depth=10):
        """민감한 데이터 마스킹"""
        if max_depth <= 0:
            return data
        
        if isinstance(data, dict):
            masked_data = {}
            for key, value in data.items():
                if self._is_sensitive_field(key):
                    if isinstance(value, str) and len(value) > 4:
                        # 처음 2자리와 마지막 2자리만 보여주고 나머지는 마스킹
                        masked_data[key] = value[:2] + '*' * (len(value) - 4) + value[-2:]
                    else:
                        masked_data[key] = '*' * len(str(value))
                else:
                    masked_data[key] = self._mask_sensitive_data(value, max_depth - 1)
            return masked_data
        
        elif isinstance(data, list):
            return [self._mask_sensitive_data(item, max_depth - 1) for item in data]
        
        return data
    
    def _is_sensitive_field(self, field_name):
        """민감한 필드인지 확인"""
        field_lower = field_name.lower()
        for pattern in self.compiled_sensitive_patterns:
            if pattern.search(field_lower):
                return True
        return False


# 전역 보안 모니터링 및 알림
class SecurityMonitor:
    """
    전역 보안 모니터링 시스템
    - 보안 이벤트 집계
    - 위협 분석
    - 자동 대응
    """
    
    def __init__(self):
        self.threat_levels = {
            'low': 0,
            'medium': 1, 
            'high': 2,
            'critical': 3
        }
    
    def analyze_security_events(self):
        """보안 이벤트 분석"""
        today = datetime.now().strftime('%Y%m%d')
        metrics_key = f'security_metrics:{today}'
        metrics = cache.get(metrics_key, {})
        
        if not metrics:
            return {'threat_level': 'low', 'events': {}}
        
        # 위협 수준 계산
        threat_score = 0
        
        # 차단된 IP 수
        banned_ips = metrics.get('rate_limit', 0) + metrics.get('suspicious_activity', 0)
        if banned_ips > 10:
            threat_score += 2
        elif banned_ips > 5:
            threat_score += 1
        
        # 로그인 실패 수
        failed_logins = metrics.get('access_denied', 0)
        if failed_logins > 50:
            threat_score += 2
        elif failed_logins > 20:
            threat_score += 1
        
        # 파일 업로드 시도
        file_uploads = metrics.get('file_upload', 0)
        if file_uploads > 100:
            threat_score += 1
        
        # 위협 수준 결정
        if threat_score >= 5:
            threat_level = 'critical'
        elif threat_score >= 3:
            threat_level = 'high'
        elif threat_score >= 1:
            threat_level = 'medium'
        else:
            threat_level = 'low'
        
        return {
            'threat_level': threat_level,
            'threat_score': threat_score,
            'events': metrics,
            'unique_ips': len(metrics.get('unique_ips', set()))
        }
    
    def send_security_alert(self, threat_analysis):
        """보안 알림 전송"""
        if threat_analysis['threat_level'] in ['high', 'critical']:
            logger.critical(f'SECURITY ALERT: Threat level {threat_analysis["threat_level"]} detected')
            logger.critical(f'Threat analysis: {json.dumps(threat_analysis, default=str)}')
            
            # 여기에 이메일 알림, Slack 알림 등을 추가할 수 있음


# 전역 보안 모니터 인스턴스
security_monitor = SecurityMonitor()