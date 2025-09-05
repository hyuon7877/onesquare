"""
종합 모니터링 및 로깅 미들웨어
상현님의 OneSquare 시스템용 성능 모니터링 및 로깅 시스템
"""
import time
import json
import logging
import threading
import psutil
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.http import JsonResponse
from django.urls import resolve
from datetime import datetime, timedelta
from collections import defaultdict
import os

# 전용 로거 설정
monitoring_logger = logging.getLogger('monitoring')
performance_logger = logging.getLogger('performance')
security_logger = logging.getLogger('security')
notion_logger = logging.getLogger('notion_api')
user_activity_logger = logging.getLogger('user_activity')


class SystemMonitoringMiddleware(MiddlewareMixin):
    """
    실시간 시스템 성능 모니터링 미들웨어
    CPU, 메모리, 디스크, 네트워크 사용률 모니터링
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.monitoring_interval = getattr(settings, 'SYSTEM_MONITORING_INTERVAL', 60)  # 1분 간격
        self.last_monitoring = 0
        self.system_stats = {
            'cpu_percent': 0,
            'memory_percent': 0,
            'disk_usage': 0,
            'network_io': {'bytes_sent': 0, 'bytes_recv': 0},
            'django_process': {'cpu_percent': 0, 'memory_percent': 0},
            'timestamp': datetime.now().isoformat()
        }
        
    def __call__(self, request):
        # 시스템 모니터링 수행 (주기적)
        current_time = time.time()
        if current_time - self.last_monitoring > self.monitoring_interval:
            self._monitor_system_resources()
            self.last_monitoring = current_time
        
        # 요청별 성능 추적 시작
        request.monitoring_start_time = time.time()
        request.monitoring_start_memory = self._get_process_memory()
        
        response = self.get_response(request)
        
        # 요청별 성능 추적 완료
        self._log_request_performance(request, response)
        
        return response
    
    def _monitor_system_resources(self):
        """시스템 리소스 모니터링"""
        try:
            # 전체 시스템 상태
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            # Django 프로세스 상태
            process = psutil.Process(os.getpid())
            django_cpu = process.cpu_percent()
            django_memory = process.memory_percent()
            
            self.system_stats = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'disk_usage_percent': disk.percent,
                'disk_free_gb': round(disk.free / (1024**3), 2),
                'network_bytes_sent': network.bytes_sent,
                'network_bytes_recv': network.bytes_recv,
                'django_process': {
                    'cpu_percent': django_cpu,
                    'memory_percent': django_memory,
                    'memory_rss_mb': round(process.memory_info().rss / (1024**2), 2),
                    'threads': process.num_threads(),
                    'open_files': len(process.open_files()),
                },
                'timestamp': datetime.now().isoformat()
            }
            
            # 캐시에 저장 (실시간 대시보드용)
            cache.set('system_monitoring_stats', self.system_stats, 300)  # 5분 캐시
            
            # 임계값 초과 시 경고 로깅
            self._check_resource_thresholds()
            
            # 상세 로깅
            monitoring_logger.info(
                'System Resources',
                extra={
                    'event_type': 'system_monitoring',
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'disk_percent': disk.percent,
                    'django_cpu': django_cpu,
                    'django_memory_mb': round(process.memory_info().rss / (1024**2), 2)
                }
            )
            
        except Exception as e:
            monitoring_logger.error(f'System monitoring error: {str(e)}')
    
    def _check_resource_thresholds(self):
        """리소스 임계값 검사 및 경고"""
        cpu_threshold = getattr(settings, 'CPU_WARNING_THRESHOLD', 80)
        memory_threshold = getattr(settings, 'MEMORY_WARNING_THRESHOLD', 85)
        disk_threshold = getattr(settings, 'DISK_WARNING_THRESHOLD', 90)
        
        if self.system_stats['cpu_percent'] > cpu_threshold:
            monitoring_logger.warning(
                f'High CPU usage: {self.system_stats["cpu_percent"]}%',
                extra={'event_type': 'resource_warning', 'metric': 'cpu'}
            )
        
        if self.system_stats['memory_percent'] > memory_threshold:
            monitoring_logger.warning(
                f'High Memory usage: {self.system_stats["memory_percent"]}%',
                extra={'event_type': 'resource_warning', 'metric': 'memory'}
            )
        
        if self.system_stats['disk_usage_percent'] > disk_threshold:
            monitoring_logger.warning(
                f'High Disk usage: {self.system_stats["disk_usage_percent"]}%',
                extra={'event_type': 'resource_warning', 'metric': 'disk'}
            )
    
    def _get_process_memory(self):
        """현재 프로세스 메모리 사용량"""
        try:
            return psutil.Process().memory_info().rss / (1024**2)  # MB
        except:
            return 0
    
    def _log_request_performance(self, request, response):
        """요청별 성능 로깅"""
        try:
            end_time = time.time()
            end_memory = self._get_process_memory()
            
            response_time = round((end_time - request.monitoring_start_time) * 1000, 2)  # ms
            memory_diff = round(end_memory - request.monitoring_start_memory, 2)  # MB
            
            # URL 패턴 및 뷰 정보
            url_pattern = 'unknown'
            view_name = 'unknown'
            try:
                resolved = resolve(request.path)
                url_pattern = resolved.url_name or resolved.view_name
                view_name = f"{resolved.func.__module__}.{resolved.func.__name__}"
            except:
                pass
            
            # 성능 로깅
            performance_logger.info(
                f'Request Performance: {request.method} {request.path}',
                extra={
                    'event_type': 'request_performance',
                    'method': request.method,
                    'path': request.path,
                    'url_pattern': url_pattern,
                    'view_name': view_name,
                    'status_code': response.status_code,
                    'response_time_ms': response_time,
                    'memory_diff_mb': memory_diff,
                    'user': str(request.user) if hasattr(request, 'user') else 'anonymous',
                    'ip_address': self._get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
                    'content_length': len(getattr(response, 'content', b'')),
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            # 느린 요청 경고 (500ms 이상)
            slow_threshold = getattr(settings, 'SLOW_REQUEST_THRESHOLD_MS', 500)
            if response_time > slow_threshold:
                monitoring_logger.warning(
                    f'Slow request detected: {response_time}ms - {request.method} {request.path}',
                    extra={
                        'event_type': 'slow_request',
                        'response_time_ms': response_time,
                        'path': request.path,
                        'view_name': view_name
                    }
                )
            
        except Exception as e:
            monitoring_logger.error(f'Request performance logging error: {str(e)}')
    
    def _get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserActivityTrackingMiddleware(MiddlewareMixin):
    """
    사용자 활동 추적 및 접근 패턴 분석 미들웨어
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.session_tracking = defaultdict(list)
        
    def __call__(self, request):
        # 사용자 활동 시작 기록
        self._track_user_activity_start(request)
        
        response = self.get_response(request)
        
        # 사용자 활동 완료 기록
        self._track_user_activity_end(request, response)
        
        return response
    
    def _track_user_activity_start(self, request):
        """사용자 활동 시작 추적"""
        request.activity_start_time = time.time()
        
        # 세션 기반 활동 추적
        session_key = request.session.session_key
        if session_key:
            activity = {
                'timestamp': datetime.now().isoformat(),
                'path': request.path,
                'method': request.method,
                'ip_address': self._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200]
            }
            
            self.session_tracking[session_key].append(activity)
            
            # 최근 100개 활동만 유지
            if len(self.session_tracking[session_key]) > 100:
                self.session_tracking[session_key] = self.session_tracking[session_key][-100:]
    
    def _track_user_activity_end(self, request, response):
        """사용자 활동 완료 추적"""
        try:
            duration = time.time() - request.activity_start_time
            
            # 인증된 사용자 활동 로깅
            if hasattr(request, 'user') and request.user.is_authenticated:
                user_activity_logger.info(
                    f'User Activity: {request.user.username}',
                    extra={
                        'event_type': 'user_activity',
                        'user_id': request.user.id,
                        'username': request.user.username,
                        'path': request.path,
                        'method': request.method,
                        'status_code': response.status_code,
                        'duration_ms': round(duration * 1000, 2),
                        'ip_address': self._get_client_ip(request),
                        'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
                        'session_key': request.session.session_key,
                        'timestamp': datetime.now().isoformat()
                    }
                )
            
            # 익명 사용자 활동 로깅
            else:
                user_activity_logger.info(
                    f'Anonymous Activity: {request.path}',
                    extra={
                        'event_type': 'anonymous_activity',
                        'path': request.path,
                        'method': request.method,
                        'status_code': response.status_code,
                        'duration_ms': round(duration * 1000, 2),
                        'ip_address': self._get_client_ip(request),
                        'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
                        'session_key': request.session.session_key,
                        'timestamp': datetime.now().isoformat()
                    }
                )
            
            # 접근 패턴 분석을 위한 캐시 업데이트
            self._update_access_patterns(request, response)
            
        except Exception as e:
            monitoring_logger.error(f'User activity tracking error: {str(e)}')
    
    def _update_access_patterns(self, request, response):
        """접근 패턴 분석 데이터 업데이트"""
        try:
            # 시간대별 접근 패턴
            hour = datetime.now().hour
            hourly_key = f'access_pattern_hourly_{hour}'
            cache.set(hourly_key, cache.get(hourly_key, 0) + 1, 86400)  # 24시간
            
            # 경로별 접근 빈도
            path_key = f'access_pattern_path_{request.path}'
            cache.set(path_key, cache.get(path_key, 0) + 1, 3600)  # 1시간
            
            # 상태 코드별 통계
            status_key = f'access_pattern_status_{response.status_code}'
            cache.set(status_key, cache.get(status_key, 0) + 1, 3600)  # 1시간
            
            # 사용자별 활동 통계 (인증된 사용자)
            if hasattr(request, 'user') and request.user.is_authenticated:
                user_key = f'user_activity_count_{request.user.id}'
                cache.set(user_key, cache.get(user_key, 0) + 1, 86400)  # 24시간
            
        except Exception as e:
            monitoring_logger.error(f'Access pattern update error: {str(e)}')
    
    def _get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class NotionAPIMonitoringMiddleware(MiddlewareMixin):
    """
    Notion API 호출 모니터링 미들웨어
    성공률, 응답시간, 에러 추적
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.notion_stats = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'avg_response_time': 0,
            'last_error': None,
            'last_updated': datetime.now().isoformat()
        }
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Notion API 관련 요청 감지 및 추적
        if self._is_notion_api_request(request):
            self._track_notion_api_call(request, response)
        
        return response
    
    def _is_notion_api_request(self, request):
        """Notion API 관련 요청인지 확인"""
        notion_patterns = ['/api/notion/', '/notion/', 'notion-api']
        return any(pattern in request.path.lower() for pattern in notion_patterns)
    
    def _track_notion_api_call(self, request, response):
        """Notion API 호출 추적"""
        try:
            self.notion_stats['total_calls'] += 1
            
            if 200 <= response.status_code < 300:
                self.notion_stats['successful_calls'] += 1
                status = 'success'
            else:
                self.notion_stats['failed_calls'] += 1
                status = 'failed'
                self.notion_stats['last_error'] = {
                    'status_code': response.status_code,
                    'path': request.path,
                    'timestamp': datetime.now().isoformat()
                }
            
            # 성공률 계산
            success_rate = (self.notion_stats['successful_calls'] / self.notion_stats['total_calls']) * 100
            
            notion_logger.info(
                f'Notion API Call: {status.upper()}',
                extra={
                    'event_type': 'notion_api_call',
                    'status': status,
                    'status_code': response.status_code,
                    'path': request.path,
                    'method': request.method,
                    'success_rate': round(success_rate, 2),
                    'total_calls': self.notion_stats['total_calls'],
                    'successful_calls': self.notion_stats['successful_calls'],
                    'failed_calls': self.notion_stats['failed_calls'],
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            # 캐시 업데이트
            cache.set('notion_api_stats', self.notion_stats, 300)  # 5분 캐시
            
            # 성공률 임계값 체크 (90% 미만 시 경고)
            if success_rate < 90 and self.notion_stats['total_calls'] > 10:
                monitoring_logger.warning(
                    f'Notion API success rate below threshold: {success_rate}%',
                    extra={
                        'event_type': 'notion_api_warning',
                        'success_rate': success_rate,
                        'total_calls': self.notion_stats['total_calls']
                    }
                )
            
        except Exception as e:
            notion_logger.error(f'Notion API monitoring error: {str(e)}')


class ErrorTrackingMiddleware(MiddlewareMixin):
    """
    에러 추적 및 알림 시스템 미들웨어
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.error_stats = defaultdict(int)
    
    def __call__(self, request):
        try:
            response = self.get_response(request)
            
            # 4xx, 5xx 에러 추적
            if response.status_code >= 400:
                self._track_error(request, response)
            
            return response
            
        except Exception as e:
            # 예외 발생 시 추적
            self._track_exception(request, e)
            raise
    
    def _track_error(self, request, response):
        """HTTP 에러 추적"""
        error_key = f'{response.status_code}_{request.path}'
        self.error_stats[error_key] += 1
        
        monitoring_logger.error(
            f'HTTP Error: {response.status_code} - {request.path}',
            extra={
                'event_type': 'http_error',
                'status_code': response.status_code,
                'path': request.path,
                'method': request.method,
                'user': str(request.user) if hasattr(request, 'user') else 'anonymous',
                'ip_address': self._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
                'referer': request.META.get('HTTP_REFERER', ''),
                'error_count': self.error_stats[error_key],
                'timestamp': datetime.now().isoformat()
            }
        )
        
        # 에러 빈도가 높으면 경고
        if self.error_stats[error_key] > 10:
            monitoring_logger.critical(
                f'High error frequency: {error_key} occurred {self.error_stats[error_key]} times',
                extra={'event_type': 'high_error_frequency', 'error_key': error_key}
            )
    
    def _track_exception(self, request, exception):
        """예외 추적"""
        exception_key = f'{exception.__class__.__name__}_{request.path}'
        self.error_stats[exception_key] += 1
        
        monitoring_logger.exception(
            f'Exception: {exception.__class__.__name__} - {request.path}',
            extra={
                'event_type': 'exception',
                'exception_type': exception.__class__.__name__,
                'exception_message': str(exception),
                'path': request.path,
                'method': request.method,
                'user': str(request.user) if hasattr(request, 'user') else 'anonymous',
                'ip_address': self._get_client_ip(request),
                'exception_count': self.error_stats[exception_key],
                'timestamp': datetime.now().isoformat()
            }
        )
    
    def _get_client_ip(self, request):
        """클라이언트 IP 주소 추출"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class DatabaseQueryMonitoringMiddleware(MiddlewareMixin):
    """
    데이터베이스 쿼리 모니터링 미들웨어
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        from django.db import connection
        
        # 쿼리 카운트 초기화
        initial_queries = len(connection.queries)
        
        response = self.get_response(request)
        
        # 쿼리 분석
        final_queries = len(connection.queries)
        query_count = final_queries - initial_queries
        
        if query_count > 0:
            # 쿼리 성능 로깅
            slow_queries = []
            total_time = 0
            
            for query in connection.queries[initial_queries:]:
                query_time = float(query['time'])
                total_time += query_time
                
                if query_time > 0.1:  # 100ms 이상인 느린 쿼리
                    slow_queries.append({
                        'sql': query['sql'][:500],  # SQL 500자 제한
                        'time': query_time
                    })
            
            monitoring_logger.info(
                f'Database Queries: {query_count} queries, {total_time:.3f}s total',
                extra={
                    'event_type': 'database_queries',
                    'query_count': query_count,
                    'total_time': round(total_time, 3),
                    'slow_queries': slow_queries,
                    'path': request.path,
                    'method': request.method,
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            # 과도한 쿼리 경고
            if query_count > 50:  # 50개 이상 쿼리 시 경고
                monitoring_logger.warning(
                    f'Excessive database queries: {query_count} queries for {request.path}',
                    extra={'event_type': 'excessive_queries', 'query_count': query_count}
                )
        
        return response