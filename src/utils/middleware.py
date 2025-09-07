"""커스텀 미들웨어"""
import time
import logging
import json
import traceback
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger('performance')
error_logger = logging.getLogger('django')


class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """요청 처리 성능 모니터링"""
    
    def process_request(self, request):
        request._start_time = time.time()
        return None
    
    def process_response(self, request, response):
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time
            
            # 느린 요청 로깅 (1초 이상)
            if duration > 1.0:
                logger.warning(
                    f"Slow request: {request.method} {request.path} "
                    f"took {duration:.2f} seconds"
                )
            
            # 성능 통계 저장
            cache_key = f"perf_stats_{request.path}"
            stats = cache.get(cache_key, {'count': 0, 'total_time': 0})
            stats['count'] += 1
            stats['total_time'] += duration
            stats['avg_time'] = stats['total_time'] / stats['count']
            cache.set(cache_key, stats, 3600)  # 1시간 캐시
            
            # 응답 헤더에 처리 시간 추가
            response['X-Response-Time'] = f"{duration:.3f}"
        
        return response


class ExceptionHandlingMiddleware(MiddlewareMixin):
    """전역 예외 처리"""
    
    def process_exception(self, request, exception):
        # 예외 로깅
        error_logger.error(
            f"Unhandled exception in {request.method} {request.path}",
            exc_info=True,
            extra={
                'request': request,
                'user': getattr(request, 'user', None),
                'ip': self.get_client_ip(request),
            }
        )
        
        # API 요청인 경우 JSON 응답
        if request.path.startswith('/api/'):
            return JsonResponse({
                'error': 'Internal server error',
                'message': str(exception) if settings.DEBUG else 'An error occurred',
                'traceback': traceback.format_exc() if settings.DEBUG else None
            }, status=500)
        
        # 일반 요청은 Django 기본 처리
        return None
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityMiddleware(MiddlewareMixin):
    """보안 관련 미들웨어"""
    
    def process_request(self, request):
        # Rate limiting
        if self.is_rate_limited(request):
            return JsonResponse({
                'error': 'Too many requests',
                'message': 'Please try again later'
            }, status=429)
        
        return None
    
    def process_response(self, request, response):
        # 보안 헤더 추가
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # HTTPS 강제
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response
    
    def is_rate_limited(self, request):
        """간단한 rate limiting 구현"""
        if settings.DEBUG:
            return False
        
        ip = self.get_client_ip(request)
        cache_key = f"rate_limit_{ip}"
        
        # 1분당 60 요청 제한
        requests = cache.get(cache_key, 0)
        if requests >= 60:
            return True
        
        cache.set(cache_key, requests + 1, 60)
        return False
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class HealthCheckMiddleware(MiddlewareMixin):
    """헬스체크 엔드포인트"""
    
    def process_request(self, request):
        if request.path == '/health/':
            return self.health_check(request)
        elif request.path == '/ready/':
            return self.readiness_check(request)
        return None
    
    def health_check(self, request):
        """기본 헬스체크"""
        return JsonResponse({
            'status': 'healthy',
            'timestamp': time.time()
        })
    
    def readiness_check(self, request):
        """준비 상태 체크"""
        checks = {
            'database': self.check_database(),
            'cache': self.check_cache(),
        }
        
        all_ready = all(checks.values())
        
        return JsonResponse({
            'status': 'ready' if all_ready else 'not_ready',
            'checks': checks,
            'timestamp': time.time()
        }, status=200 if all_ready else 503)
    
    def check_database(self):
        """데이터베이스 연결 확인"""
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return True
        except Exception:
            return False
    
    def check_cache(self):
        """캐시 연결 확인"""
        try:
            cache.set('health_check', 'ok', 1)
            return cache.get('health_check') == 'ok'
        except Exception:
            return False