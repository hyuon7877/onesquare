"""침입 탐지 시스템 미들웨어"""
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
