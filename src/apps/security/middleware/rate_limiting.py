"""Rate Limiting 미들웨어"""
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
