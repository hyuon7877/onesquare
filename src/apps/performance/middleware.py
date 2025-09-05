"""
OneSquare 성능 최적화 미들웨어

Django 백엔드 성능 최적화를 위한 미들웨어 모음:
- 응답 압축 및 최적화
- 캐시 헤더 최적화
- 데이터베이스 쿼리 최적화
- API 성능 모니터링
- 메모리 사용량 최적화
"""

import time
import gzip
import json
import logging
from io import BytesIO
from django.conf import settings
from django.core.cache import cache, caches
from django.db import connection
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.utils.cache import patch_response_headers
from django.utils.http import http_date
from datetime import datetime, timedelta
import psutil
import threading

logger = logging.getLogger('apps.performance')


class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """
    성능 모니터링 미들웨어
    - 요청/응답 시간 측정
    - 데이터베이스 쿼리 수 측정
    - 메모리 사용량 모니터링
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.enable_query_logging = getattr(settings, 'PERFORMANCE_MONITORING', {}).get('ENABLE_QUERY_LOGGING', False)
        self.enable_memory_monitoring = getattr(settings, 'PERFORMANCE_MONITORING', {}).get('ENABLE_MEMORY_MONITORING', False)
        self.slow_query_threshold = getattr(settings, 'PERFORMANCE_MONITORING', {}).get('SLOW_QUERY_THRESHOLD', 1.0)
    
    def process_request(self, request):
        """요청 처리 시작 시점 기록"""
        request._performance_start_time = time.time()
        request._performance_start_queries = len(connection.queries) if self.enable_query_logging else 0
        
        if self.enable_memory_monitoring:
            process = psutil.Process()
            request._performance_start_memory = process.memory_info().rss
        
        return None
    
    def process_response(self, request, response):
        """응답 처리 완료 시점에서 성능 메트릭 수집"""
        if not hasattr(request, '_performance_start_time'):
            return response
        
        # 응답 시간 계산
        total_time = time.time() - request._performance_start_time
        
        # 데이터베이스 쿼리 수 계산
        if self.enable_query_logging:
            query_count = len(connection.queries) - request._performance_start_queries
        else:
            query_count = 0
        
        # 메모리 사용량 계산
        memory_usage = 0
        if self.enable_memory_monitoring and hasattr(request, '_performance_start_memory'):
            process = psutil.Process()
            current_memory = process.memory_info().rss
            memory_usage = current_memory - request._performance_start_memory
        
        # 성능 헤더 추가
        response['X-Response-Time'] = f'{total_time:.3f}s'
        if self.enable_query_logging:
            response['X-DB-Queries'] = str(query_count)
        if self.enable_memory_monitoring:
            response['X-Memory-Usage'] = f'{memory_usage}B'
        
        # 느린 요청 로깅
        if total_time > self.slow_query_threshold:
            logger.warning(
                f'Slow request: {request.method} {request.path} - '
                f'Time: {total_time:.3f}s, Queries: {query_count}, Memory: {memory_usage}B'
            )
        
        # 성능 메트릭을 캐시에 저장 (분석용)
        self._store_performance_metrics(request, total_time, query_count, memory_usage)
        
        return response
    
    def _store_performance_metrics(self, request, response_time, query_count, memory_usage):
        """성능 메트릭을 캐시에 저장"""
        try:
            cache_key = f'performance_metrics:{datetime.now().strftime("%Y%m%d_%H")}'
            metrics = cache.get(cache_key, [])
            
            metrics.append({
                'timestamp': datetime.now().isoformat(),
                'method': request.method,
                'path': request.path,
                'response_time': response_time,
                'query_count': query_count,
                'memory_usage': memory_usage,
                'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None
            })
            
            # 최대 1000개 메트릭만 유지
            if len(metrics) > 1000:
                metrics = metrics[-1000:]
            
            cache.set(cache_key, metrics, 3600)  # 1시간 보관
            
        except Exception as e:
            logger.error(f'Failed to store performance metrics: {e}')


class ResponseCompressionMiddleware(MiddlewareMixin):
    """
    응답 압축 미들웨어
    - Gzip 압축 적용
    - 압축 조건 최적화
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.min_length = 1024  # 1KB 이상만 압축
        self.compressible_types = [
            'text/html',
            'text/css', 
            'text/javascript',
            'application/javascript',
            'application/json',
            'application/xml',
            'text/xml',
            'text/plain',
        ]
    
    def process_response(self, request, response):
        """응답을 압축 처리"""
        # 이미 압축된 응답은 건너뛰기
        if response.get('Content-Encoding'):
            return response
        
        # Content-Length 확인
        if not response.get('Content-Length'):
            return response
        
        content_length = int(response['Content-Length'])
        
        # 최소 크기 미만은 압축하지 않음
        if content_length < self.min_length:
            return response
        
        # Content-Type 확인
        content_type = response.get('Content-Type', '').lower()
        compressible = any(ct in content_type for ct in self.compressible_types)
        
        if not compressible:
            return response
        
        # Accept-Encoding 헤더 확인
        accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
        if 'gzip' not in accept_encoding:
            return response
        
        # Gzip 압축 적용
        try:
            compressed_content = self._compress_response(response.content)
            
            if len(compressed_content) < content_length:
                response.content = compressed_content
                response['Content-Encoding'] = 'gzip'
                response['Content-Length'] = str(len(compressed_content))
                response['Vary'] = 'Accept-Encoding'
                
                logger.debug(f'Response compressed: {content_length} -> {len(compressed_content)} bytes')
            
        except Exception as e:
            logger.error(f'Failed to compress response: {e}')
        
        return response
    
    def _compress_response(self, content):
        """내용을 Gzip으로 압축"""
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        buffer = BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='wb', compresslevel=6) as f:
            f.write(content)
        
        return buffer.getvalue()


class CacheOptimizationMiddleware(MiddlewareMixin):
    """
    캐시 최적화 미들웨어
    - 스마트 캐시 헤더 설정
    - ETag 생성 및 검증
    - Last-Modified 헤더 관리
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.api_cache_config = getattr(settings, 'API_RESPONSE_OPTIMIZATION', {})
        self.enable_etag = self.api_cache_config.get('ENABLE_ETAG', True)
        self.enable_last_modified = self.api_cache_config.get('ENABLE_LAST_MODIFIED', True)
        self.cache_control_max_age = self.api_cache_config.get('CACHE_CONTROL_MAX_AGE', 300)
    
    def process_response(self, request, response):
        """캐시 헤더 최적화"""
        # API 응답에만 적용
        if not request.path.startswith('/api/'):
            return response
        
        # 성공한 GET 요청에만 캐시 헤더 적용
        if request.method != 'GET' or response.status_code != 200:
            return response
        
        # Cache-Control 헤더 설정
        if not response.get('Cache-Control'):
            cache_control = f'public, max-age={self.cache_control_max_age}'
            
            # 사용자별 데이터는 private 캐시
            if hasattr(request, 'user') and request.user.is_authenticated:
                if any(keyword in request.path for keyword in ['/dashboard/', '/profile/', '/notifications/']):
                    cache_control = f'private, max-age={self.cache_control_max_age // 2}'
            
            response['Cache-Control'] = cache_control
        
        # ETag 헤더 생성
        if self.enable_etag and not response.get('ETag'):
            etag = self._generate_etag(response)
            if etag:
                response['ETag'] = etag
                
                # If-None-Match 헤더 검증
                if_none_match = request.META.get('HTTP_IF_NONE_MATCH')
                if if_none_match == etag:
                    return HttpResponse(status=304)
        
        # Last-Modified 헤더 설정
        if self.enable_last_modified and not response.get('Last-Modified'):
            last_modified = self._get_last_modified(request)
            if last_modified:
                response['Last-Modified'] = http_date(last_modified.timestamp())
                
                # If-Modified-Since 헤더 검증
                if_modified_since = request.META.get('HTTP_IF_MODIFIED_SINCE')
                if if_modified_since:
                    try:
                        if_modified_time = datetime.fromisoformat(if_modified_since.replace('GMT', '+00:00'))
                        if last_modified <= if_modified_time:
                            return HttpResponse(status=304)
                    except (ValueError, TypeError):
                        pass
        
        # Vary 헤더 추가
        vary_headers = ['Accept-Encoding']
        if hasattr(request, 'user') and request.user.is_authenticated:
            vary_headers.append('Authorization')
        
        response['Vary'] = ', '.join(vary_headers)
        
        return response
    
    def _generate_etag(self, response):
        """응답 내용 기반 ETag 생성"""
        try:
            import hashlib
            content = response.content
            if isinstance(content, str):
                content = content.encode('utf-8')
            
            return f'"{hashlib.md5(content).hexdigest()}"'
        except Exception:
            return None
    
    def _get_last_modified(self, request):
        """리소스의 최종 수정 시간 조회"""
        # 캐시에서 최종 수정 시간 조회
        cache_key = f'last_modified:{request.path}'
        last_modified = cache.get(cache_key)
        
        if not last_modified:
            # 기본값: 현재 시간에서 5분 전
            last_modified = datetime.now() - timedelta(minutes=5)
            cache.set(cache_key, last_modified, 3600)  # 1시간 캐시
        
        return last_modified


class QueryOptimizationMiddleware(MiddlewareMixin):
    """
    데이터베이스 쿼리 최적화 미들웨어
    - N+1 쿼리 감지
    - 중복 쿼리 방지
    - 쿼리 결과 캐싱
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.query_cache = caches['default']
        self.enable_query_caching = True
        self.cache_timeout = 300  # 5분
    
    def process_request(self, request):
        """요청 시작 시 쿼리 추적 시작"""
        request._query_start_count = len(connection.queries)
        request._duplicate_queries = {}
        return None
    
    def process_response(self, request, response):
        """쿼리 최적화 분석 및 캐싱"""
        if not hasattr(request, '_query_start_count'):
            return response
        
        # 실행된 쿼리 수 계산
        current_queries = connection.queries[request._query_start_count:]
        query_count = len(current_queries)
        
        # 중복 쿼리 감지
        duplicate_count = 0
        query_signatures = {}
        
        for query in current_queries:
            signature = self._get_query_signature(query['sql'])
            if signature in query_signatures:
                duplicate_count += 1
                logger.warning(f'Duplicate query detected: {signature}')
            else:
                query_signatures[signature] = 1
        
        # N+1 쿼리 감지 (같은 패턴의 쿼리가 많은 경우)
        if query_count > 10:
            pattern_counts = {}
            for query in current_queries:
                pattern = self._get_query_pattern(query['sql'])
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
            
            for pattern, count in pattern_counts.items():
                if count > 5:  # 같은 패턴이 5번 이상 실행됨
                    logger.warning(f'Potential N+1 query: {pattern} (executed {count} times)')
        
        # 쿼리 결과 캐싱 (GET 요청만)
        if request.method == 'GET' and response.status_code == 200 and query_count > 0:
            self._cache_query_result(request, response)
        
        return response
    
    def _get_query_signature(self, sql):
        """쿼리의 고유 서명 생성 (매개변수 제거)"""
        import re
        # 숫자와 문자열 리터럴을 플레이스홀더로 대체
        signature = re.sub(r'\b\d+\b', '?', sql)
        signature = re.sub(r"'[^']*'", '?', signature)
        signature = re.sub(r'"[^"]*"', '?', signature)
        return signature.strip()
    
    def _get_query_pattern(self, sql):
        """쿼리 패턴 추출 (테이블명과 기본 구조)"""
        import re
        # SELECT, INSERT, UPDATE, DELETE 패턴 추출
        pattern = re.sub(r'\b\d+\b', '?', sql)
        pattern = re.sub(r"'[^']*'", '?', pattern)
        pattern = re.sub(r'"[^"]*"', '?', pattern)
        # WHERE 절 이후 간소화
        pattern = re.sub(r'WHERE.*', 'WHERE ...', pattern, flags=re.IGNORECASE)
        return pattern.strip()[:100]  # 처음 100자만
    
    def _cache_query_result(self, request, response):
        """쿼리 결과를 캐시에 저장"""
        if not self.enable_query_caching:
            return
        
        try:
            cache_key = f'query_result:{request.method}:{request.path}:{request.GET.urlencode()}'
            
            # API 응답만 캐시
            if request.path.startswith('/api/') and response['Content-Type'].startswith('application/json'):
                self.query_cache.set(
                    cache_key,
                    {
                        'content': response.content.decode('utf-8'),
                        'headers': dict(response.items()),
                        'status_code': response.status_code
                    },
                    self.cache_timeout
                )
                logger.debug(f'Query result cached: {cache_key}')
                
        except Exception as e:
            logger.error(f'Failed to cache query result: {e}')


class APIRateLimitMiddleware(MiddlewareMixin):
    """
    API 속도 제한 미들웨어
    - 사용자별/IP별 요청 제한
    - 적응형 속도 제한
    - 남용 방지
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.rate_limits = {
            'authenticated': {'requests': 1000, 'window': 3600},  # 1시간에 1000회
            'anonymous': {'requests': 100, 'window': 3600},       # 1시간에 100회
            'api_heavy': {'requests': 50, 'window': 3600},        # 무거운 API는 50회
        }
        
    def process_request(self, request):
        """요청 속도 제한 검사"""
        if not request.path.startswith('/api/'):
            return None
        
        # 사용자 식별
        user_key = self._get_user_key(request)
        
        # 속도 제한 유형 결정
        limit_type = self._get_limit_type(request)
        
        # 현재 요청 수 확인
        current_requests = self._get_current_requests(user_key, limit_type)
        max_requests = self.rate_limits[limit_type]['requests']
        
        if current_requests >= max_requests:
            logger.warning(f'Rate limit exceeded: {user_key} ({current_requests}/{max_requests})')
            return HttpResponse(
                json.dumps({
                    'error': 'Rate limit exceeded',
                    'retry_after': self.rate_limits[limit_type]['window']
                }),
                status=429,
                content_type='application/json'
            )
        
        # 요청 수 증가
        self._increment_requests(user_key, limit_type)
        
        return None
    
    def _get_user_key(self, request):
        """사용자 식별 키 생성"""
        if hasattr(request, 'user') and request.user.is_authenticated:
            return f'user:{request.user.id}'
        else:
            return f'ip:{self._get_client_ip(request)}'
    
    def _get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR', 'unknown')
    
    def _get_limit_type(self, request):
        """속도 제한 유형 결정"""
        # 무거운 API 경로들
        heavy_paths = ['/api/reports/generate/', '/api/analytics/', '/api/export/']
        
        if any(path in request.path for path in heavy_paths):
            return 'api_heavy'
        
        if hasattr(request, 'user') and request.user.is_authenticated:
            return 'authenticated'
        else:
            return 'anonymous'
    
    def _get_current_requests(self, user_key, limit_type):
        """현재 요청 수 조회"""
        cache_key = f'rate_limit:{limit_type}:{user_key}'
        return cache.get(cache_key, 0)
    
    def _increment_requests(self, user_key, limit_type):
        """요청 수 증가"""
        cache_key = f'rate_limit:{limit_type}:{user_key}'
        window = self.rate_limits[limit_type]['window']
        
        try:
            current = cache.get(cache_key, 0)
            cache.set(cache_key, current + 1, window)
        except Exception as e:
            logger.error(f'Failed to increment rate limit counter: {e}')


class MemoryOptimizationMiddleware(MiddlewareMixin):
    """
    메모리 사용량 최적화 미들웨어
    - 메모리 누수 감지
    - 대용량 응답 스트리밍
    - 가비지 컬렉션 최적화
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.memory_threshold = 100 * 1024 * 1024  # 100MB
        self.large_response_threshold = 1024 * 1024  # 1MB
    
    def process_request(self, request):
        """요청 시작 시 메모리 상태 기록"""
        try:
            process = psutil.Process()
            request._memory_start = process.memory_info().rss
        except Exception:
            request._memory_start = 0
        
        return None
    
    def process_response(self, request, response):
        """메모리 사용량 최적화"""
        # 메모리 사용량 확인
        if hasattr(request, '_memory_start') and request._memory_start > 0:
            try:
                process = psutil.Process()
                current_memory = process.memory_info().rss
                memory_delta = current_memory - request._memory_start
                
                # 메모리 사용량이 임계값을 초과한 경우
                if memory_delta > self.memory_threshold:
                    logger.warning(f'High memory usage: {memory_delta / 1024 / 1024:.2f}MB for {request.path}')
                    
                    # 강제 가비지 컬렉션
                    import gc
                    gc.collect()
                
            except Exception as e:
                logger.error(f'Memory monitoring failed: {e}')
        
        # 대용량 응답 스트리밍 처리
        if hasattr(response, 'content') and len(response.content) > self.large_response_threshold:
            response = self._optimize_large_response(response)
        
        return response
    
    def _optimize_large_response(self, response):
        """대용량 응답 최적화"""
        try:
            # 이미 스트리밍 응답인 경우 건너뛰기
            if hasattr(response, 'streaming') and response.streaming:
                return response
            
            # JSON 응답인 경우 청크 단위로 분할
            if response.get('Content-Type', '').startswith('application/json'):
                content = response.content
                if isinstance(content, bytes):
                    content = content.decode('utf-8')
                
                # 큰 JSON 응답을 청크로 분할
                def json_chunks(content, chunk_size=8192):
                    for i in range(0, len(content), chunk_size):
                        yield content[i:i + chunk_size].encode('utf-8')
                
                response = HttpResponse(
                    json_chunks(content),
                    content_type=response.get('Content-Type'),
                    status=response.status_code
                )
                response.streaming = True
            
        except Exception as e:
            logger.error(f'Failed to optimize large response: {e}')
        
        return response


# 전역 성능 모니터링 스레드
class GlobalPerformanceMonitor:
    """
    전역 성능 모니터링
    - 시스템 리소스 모니터링
    - 성능 알림
    - 자동 최적화
    """
    
    def __init__(self):
        self.monitoring_thread = None
        self.is_monitoring = False
        self.metrics = {
            'cpu_usage': [],
            'memory_usage': [],
            'disk_usage': [],
            'active_connections': 0
        }
    
    def start_monitoring(self):
        """모니터링 시작"""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitoring_thread = threading.Thread(target=self._monitor_loop)
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()
            logger.info('Global performance monitoring started')
    
    def stop_monitoring(self):
        """모니터링 중단"""
        self.is_monitoring = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info('Global performance monitoring stopped')
    
    def _monitor_loop(self):
        """모니터링 루프"""
        while self.is_monitoring:
            try:
                # 시스템 메트릭 수집
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # 메트릭 저장
                self.metrics['cpu_usage'].append(cpu_percent)
                self.metrics['memory_usage'].append(memory.percent)
                self.metrics['disk_usage'].append(disk.percent)
                
                # 최근 100개 데이터점만 유지
                for key in ['cpu_usage', 'memory_usage', 'disk_usage']:
                    if len(self.metrics[key]) > 100:
                        self.metrics[key] = self.metrics[key][-100:]
                
                # 임계값 확인
                self._check_thresholds(cpu_percent, memory.percent, disk.percent)
                
                # 60초 간격
                time.sleep(60)
                
            except Exception as e:
                logger.error(f'Performance monitoring error: {e}')
                time.sleep(60)
    
    def _check_thresholds(self, cpu_percent, memory_percent, disk_percent):
        """임계값 확인 및 알림"""
        if cpu_percent > 80:
            logger.warning(f'High CPU usage: {cpu_percent}%')
        
        if memory_percent > 85:
            logger.warning(f'High memory usage: {memory_percent}%')
        
        if disk_percent > 90:
            logger.warning(f'High disk usage: {disk_percent}%')
    
    def get_metrics(self):
        """현재 메트릭 반환"""
        return self.metrics.copy()


# 전역 모니터 인스턴스
global_monitor = GlobalPerformanceMonitor()

# Django 앱 시작 시 모니터링 시작
def start_global_monitoring():
    """전역 모니터링 시작"""
    global_monitor.start_monitoring()

def stop_global_monitoring():
    """전역 모니터링 중단"""
    global_monitor.stop_monitoring()