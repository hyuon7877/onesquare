"""
모니터링 대시보드 뷰
실시간 시스템 모니터링 및 분석 대시보드
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.core.cache import cache
from django.db.models import Count, Avg, Max, Min, Q
from datetime import datetime, timedelta
import json
import psutil
import os

from .models import (
    SystemMetrics, RequestMetrics, UserActivity, 
    NotionAPIMetrics, ErrorLog, PerformanceAlert
)


@method_decorator(staff_member_required, name='dispatch')
class MonitoringDashboardView(TemplateView):
    """메인 모니터링 대시보드"""
    template_name = 'monitoring/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 실시간 시스템 상태
        context['system_status'] = self.get_system_status()
        
        # 최근 알림
        context['recent_alerts'] = PerformanceAlert.get_unacknowledged_alerts()[:10]
        
        # 에러 요약
        context['error_summary'] = self.get_error_summary()
        
        # Notion API 상태
        context['notion_status'] = self.get_notion_api_status()
        
        # 사용자 활동 요약
        context['user_activity_summary'] = self.get_user_activity_summary()
        
        return context
    
    def get_system_status(self):
        """현재 시스템 상태 반환"""
        try:
            # 캐시된 시스템 상태 먼저 확인
            cached_stats = cache.get('system_monitoring_stats')
            if cached_stats:
                return cached_stats
            
            # 실시간 시스템 정보 수집
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            process = psutil.Process(os.getpid())
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'disk_usage_percent': disk.percent,
                'disk_free_gb': round(disk.free / (1024**3), 2),
                'django_process': {
                    'cpu_percent': process.cpu_percent(),
                    'memory_percent': process.memory_percent(),
                    'memory_rss_mb': round(process.memory_info().rss / (1024**2), 2),
                },
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_error_summary(self):
        """에러 요약 정보"""
        try:
            # 최근 24시간 에러
            since_24h = datetime.now() - timedelta(hours=24)
            
            total_errors = ErrorLog.objects.filter(timestamp__gte=since_24h).count()
            unresolved_errors = ErrorLog.get_unresolved_errors().count()
            critical_errors = ErrorLog.objects.filter(
                timestamp__gte=since_24h,
                level='CRITICAL'
            ).count()
            
            # 에러 타입별 분포
            error_types = ErrorLog.objects.filter(
                timestamp__gte=since_24h
            ).values('error_type').annotate(
                count=Count('id')
            ).order_by('-count')[:5]
            
            return {
                'total_errors': total_errors,
                'unresolved_errors': unresolved_errors,
                'critical_errors': critical_errors,
                'error_types': list(error_types)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_notion_api_status(self):
        """Notion API 상태 정보"""
        try:
            # 최근 1시간 데이터
            since_1h = datetime.now() - timedelta(hours=1)
            
            recent_calls = NotionAPIMetrics.objects.filter(timestamp__gte=since_1h)
            
            if not recent_calls.exists():
                return {
                    'success_rate': 100.0,
                    'avg_response_time': 0,
                    'total_calls': 0,
                    'status': 'no_data'
                }
            
            total_calls = recent_calls.count()
            successful_calls = recent_calls.filter(is_success=True).count()
            success_rate = (successful_calls / total_calls) * 100 if total_calls > 0 else 100
            
            avg_response_time = recent_calls.aggregate(
                avg_time=Avg('response_time_ms')
            )['avg_time'] or 0
            
            # 상태 판정
            status = 'excellent'
            if success_rate < 95:
                status = 'warning'
            if success_rate < 90:
                status = 'critical'
            
            return {
                'success_rate': round(success_rate, 2),
                'avg_response_time': round(avg_response_time, 2),
                'total_calls': total_calls,
                'successful_calls': successful_calls,
                'status': status
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_user_activity_summary(self):
        """사용자 활동 요약"""
        try:
            # 최근 1시간 활성 사용자
            active_users_1h = UserActivity.get_active_users(hours=1)
            
            # 최근 24시간 총 활동
            since_24h = datetime.now() - timedelta(hours=24)
            total_activities = UserActivity.objects.filter(timestamp__gte=since_24h).count()
            
            # 인기 페이지 (최근 24시간)
            popular_pages = UserActivity.objects.filter(
                timestamp__gte=since_24h
            ).values('path').annotate(
                visit_count=Count('id')
            ).order_by('-visit_count')[:5]
            
            return {
                'active_users_1h': active_users_1h,
                'total_activities_24h': total_activities,
                'popular_pages': list(popular_pages)
            }
        except Exception as e:
            return {'error': str(e)}


@staff_member_required
def system_metrics_api(request):
    """시스템 메트릭 API (실시간 차트용)"""
    try:
        # 시간 범위 파라미터
        hours = int(request.GET.get('hours', 1))
        
        # 시스템 메트릭 조회
        metrics = SystemMetrics.get_recent_metrics(hours=hours)
        
        data = {
            'timestamps': [m.timestamp.isoformat() for m in metrics],
            'cpu_percent': [m.cpu_percent for m in metrics],
            'memory_percent': [m.memory_percent for m in metrics],
            'django_cpu_percent': [m.django_cpu_percent for m in metrics],
            'django_memory_rss_mb': [m.django_memory_rss_mb for m in metrics],
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
def performance_metrics_api(request):
    """성능 메트릭 API"""
    try:
        hours = int(request.GET.get('hours', 1))
        since = datetime.now() - timedelta(hours=hours)
        
        # 응답 시간 분포
        response_times = RequestMetrics.objects.filter(
            timestamp__gte=since
        ).values_list('response_time_ms', flat=True)
        
        # 상태 코드 분포
        status_codes = RequestMetrics.objects.filter(
            timestamp__gte=since
        ).values('status_code').annotate(
            count=Count('id')
        ).order_by('status_code')
        
        # 느린 요청 Top 10
        slow_requests = RequestMetrics.get_slow_requests(
            threshold_ms=500, hours=hours
        )[:10]
        
        # 인기 엔드포인트
        popular_endpoints = RequestMetrics.get_popular_endpoints(hours=hours)
        
        data = {
            'response_times': list(response_times),
            'status_codes': list(status_codes),
            'slow_requests': [
                {
                    'path': req.path,
                    'method': req.method,
                    'response_time_ms': req.response_time_ms,
                    'timestamp': req.timestamp.isoformat()
                } for req in slow_requests
            ],
            'popular_endpoints': list(popular_endpoints)
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
def notion_api_metrics_api(request):
    """Notion API 메트릭 API"""
    try:
        hours = int(request.GET.get('hours', 24))
        
        # 성공률 트렌드
        success_rate = NotionAPIMetrics.get_success_rate(hours=hours)
        avg_response_time = NotionAPIMetrics.get_average_response_time(hours=hours)
        
        # 시간대별 호출 패턴
        since = datetime.now() - timedelta(hours=hours)
        hourly_calls = NotionAPIMetrics.objects.filter(
            timestamp__gte=since
        ).extra(
            select={'hour': "strftime('%%H', timestamp)"}
        ).values('hour').annotate(
            total_calls=Count('id'),
            successful_calls=Count('id', filter=Q(is_success=True)),
            failed_calls=Count('id', filter=Q(is_success=False))
        ).order_by('hour')
        
        # 에러 유형별 분포
        error_summary = NotionAPIMetrics.get_error_summary(hours=hours)
        
        data = {
            'success_rate': success_rate,
            'avg_response_time': avg_response_time,
            'hourly_calls': list(hourly_calls),
            'error_summary': list(error_summary)
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
def user_activity_api(request):
    """사용자 활동 API"""
    try:
        hours = int(request.GET.get('hours', 24))
        since = datetime.now() - timedelta(hours=hours)
        
        # 시간대별 활성 사용자
        hourly_activity = UserActivity.objects.filter(
            timestamp__gte=since
        ).extra(
            select={'hour': "strftime('%%H', timestamp)"}
        ).values('hour').annotate(
            total_activities=Count('id'),
            authenticated_activities=Count('id', filter=Q(is_authenticated=True)),
            unique_users=Count('user', distinct=True, filter=Q(is_authenticated=True))
        ).order_by('hour')
        
        # 인기 페이지
        popular_pages = UserActivity.objects.filter(
            timestamp__gte=since
        ).values('path').annotate(
            visit_count=Count('id'),
            unique_visitors=Count('user', distinct=True)
        ).order_by('-visit_count')[:10]
        
        # 최근 활동
        recent_activities = UserActivity.objects.filter(
            timestamp__gte=datetime.now() - timedelta(minutes=30)
        ).select_related('user')[:20]
        
        data = {
            'hourly_activity': list(hourly_activity),
            'popular_pages': list(popular_pages),
            'recent_activities': [
                {
                    'user': activity.user.username if activity.user else 'Anonymous',
                    'path': activity.path,
                    'method': activity.method,
                    'duration_ms': activity.duration_ms,
                    'timestamp': activity.timestamp.isoformat()
                } for activity in recent_activities
            ]
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
def error_logs_api(request):
    """에러 로그 API"""
    try:
        hours = int(request.GET.get('hours', 24))
        since = datetime.now() - timedelta(hours=hours)
        
        # 최근 에러 로그
        recent_errors = ErrorLog.objects.filter(
            timestamp__gte=since
        ).order_by('-timestamp')[:50]
        
        # 에러 타입별 분포
        error_frequency = ErrorLog.get_error_frequency(hours=hours)
        
        # 시간대별 에러 발생
        hourly_errors = ErrorLog.objects.filter(
            timestamp__gte=since
        ).extra(
            select={'hour': "strftime('%%H', timestamp)"}
        ).values('hour').annotate(
            total_errors=Count('id'),
            critical_errors=Count('id', filter=Q(level='CRITICAL')),
            warnings=Count('id', filter=Q(level='WARNING'))
        ).order_by('hour')
        
        data = {
            'recent_errors': [
                {
                    'id': error.id,
                    'timestamp': error.timestamp.isoformat(),
                    'error_type': error.error_type,
                    'level': error.level,
                    'message': error.message[:200],
                    'path': error.path,
                    'is_resolved': error.is_resolved
                } for error in recent_errors
            ],
            'error_frequency': list(error_frequency),
            'hourly_errors': list(hourly_errors)
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
def alerts_api(request):
    """알림 API"""
    try:
        if request.method == 'GET':
            # 미확인 알림 목록
            unacknowledged_alerts = PerformanceAlert.get_unacknowledged_alerts()[:20]
            
            data = {
                'alerts': [
                    {
                        'id': alert.id,
                        'timestamp': alert.timestamp.isoformat(),
                        'alert_type': alert.alert_type,
                        'severity': alert.severity,
                        'message': alert.message,
                        'actual_value': alert.actual_value,
                        'threshold_value': alert.threshold_value,
                        'related_path': alert.related_path
                    } for alert in unacknowledged_alerts
                ]
            }
            
            return JsonResponse(data)
            
        elif request.method == 'POST':
            # 알림 확인 처리
            data = json.loads(request.body)
            alert_id = data.get('alert_id')
            
            try:
                alert = PerformanceAlert.objects.get(id=alert_id)
                alert.acknowledge(user=request.user)
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Alert acknowledged successfully'
                })
                
            except PerformanceAlert.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Alert not found'
                }, status=404)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
def health_check_api(request):
    """시스템 헬스 체크 API"""
    try:
        # 데이터베이스 연결 확인
        db_status = 'ok'
        try:
            from django.db import connection
            connection.ensure_connection()
        except Exception:
            db_status = 'error'
        
        # 캐시 연결 확인
        cache_status = 'ok'
        try:
            cache.set('health_check', 'ok', 10)
            if cache.get('health_check') != 'ok':
                cache_status = 'error'
        except Exception:
            cache_status = 'error'
        
        # 디스크 공간 확인
        disk = psutil.disk_usage('/')
        disk_free_gb = disk.free / (1024**3)
        disk_status = 'ok' if disk_free_gb > 1.0 else 'warning'  # 1GB 미만 시 경고
        
        # 메모리 사용률 확인
        memory = psutil.virtual_memory()
        memory_status = 'ok' if memory.percent < 90 else 'warning'
        
        # 전체 상태 판정
        overall_status = 'ok'
        if any(status != 'ok' for status in [db_status, cache_status, disk_status, memory_status]):
            overall_status = 'warning'
        if db_status == 'error' or cache_status == 'error':
            overall_status = 'error'
        
        data = {
            'status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'checks': {
                'database': db_status,
                'cache': cache_status,
                'disk': disk_status,
                'memory': memory_status
            },
            'metrics': {
                'disk_free_gb': round(disk_free_gb, 2),
                'memory_percent': memory.percent,
                'cpu_percent': psutil.cpu_percent(interval=1)
            }
        }
        
        return JsonResponse(data)
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }, status=500)