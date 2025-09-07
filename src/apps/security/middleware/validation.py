"""입력 데이터 검증 미들웨어"""
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
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION)\b)",
        r"(--|#|/\*|\*/)",
        r"(\bOR\b\s*\d+\s*=\s*\d+)",
        r"('\s*(OR|AND)\s+)",
    ]
    
    # XSS 패턴
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
        r"<object",
        r"<embed",
        r"<applet",
        r"<meta",
        r"<link",
        r"<style",
        r"expression\s*\(",
        r"vbscript:",
        r"data:text/html",
    ]
    
    # 경로 탐색 패턴
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"%2e%2e[/\\]",
        r"\.\.%2f",
        r"\.\.%5c",
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
