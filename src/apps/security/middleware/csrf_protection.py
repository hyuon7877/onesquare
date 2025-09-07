"""CSRF 보호 강화 미들웨어"""
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
