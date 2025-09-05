"""
OneSquare 통합 관리 대시보드 시스템 - 서비스 레이어
데이터 수집, 처리, 캐싱 및 실시간 업데이트 서비스
"""

from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q, F
from django.contrib.auth import get_user_model
from django.core.cache import cache
from datetime import datetime, timedelta
from decimal import Decimal
import json
import hashlib

from apps.revenue.models import RevenueRecord, Project, Client, RevenueTarget
from apps.calendar_system.models import CalendarEvent
from apps.auth_system.models import CustomUser
from .models import (
    DashboardDataCache, SystemHealthMetric, 
    DashboardNotification, NotificationReadStatus
)

User = get_user_model()


class DashboardDataService:
    """대시보드 데이터 서비스"""
    
    def __init__(self):
        self.cache_timeout = 300  # 5분
    
    def get_dashboard_overview(self, user):
        """대시보드 전체 개요 데이터 조회"""
        
        cache_key = f"dashboard_overview_{user.id}_{user.user_type}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        overview_data = {
            'user_info': self._get_user_info(user),
            'quick_stats': self._get_quick_stats(user),
            'recent_activities': self._get_recent_activities(user),
            'system_alerts': self._get_system_alerts(user),
            'last_updated': timezone.now().isoformat()
        }
        
        # 권한별 추가 데이터
        if user.user_type in ['SUPER_ADMIN', 'MANAGER']:
            overview_data.update({
                'revenue_summary': self._get_revenue_summary(user),
                'team_performance': self._get_team_performance(user),
            })
        
        cache.set(cache_key, overview_data, self.cache_timeout)
        return overview_data
    
    def get_widget_data(self, widget_type, data_source, user, time_range='7d'):
        """특정 위젯 데이터 조회"""
        
        cache_key = f"widget_{widget_type}_{data_source}_{user.id}_{time_range}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        widget_data = {}
        
        # 위젯 타입별 데이터 처리
        if widget_type == 'chart_pie':
            widget_data = self._get_pie_chart_data(data_source, user, time_range)
        elif widget_type == 'chart_bar':
            widget_data = self._get_bar_chart_data(data_source, user, time_range)
        elif widget_type == 'chart_line':
            widget_data = self._get_line_chart_data(data_source, user, time_range)
        elif widget_type == 'stats_card':
            widget_data = self._get_stats_card_data(data_source, user, time_range)
        elif widget_type == 'table':
            widget_data = self._get_table_data(data_source, user, time_range)
        elif widget_type == 'calendar':
            widget_data = self._get_calendar_widget_data(user, time_range)
        elif widget_type == 'progress':
            widget_data = self._get_progress_data(data_source, user, time_range)
        else:
            widget_data = {'error': 'Unsupported widget type'}
        
        widget_data['last_updated'] = timezone.now().isoformat()
        
        cache.set(cache_key, widget_data, self.cache_timeout)
        return widget_data
    
    def get_revenue_dashboard_data(self, user):
        """매출 대시보드 데이터 조회"""
        
        if user.user_type not in ['SUPER_ADMIN', 'MANAGER']:
            return {'error': '접근 권한이 없습니다.'}
        
        cache_key = f"revenue_dashboard_{user.id}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        # 현재 월/년도
        now = timezone.now()
        current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # 매출 통계
        revenue_stats = {
            'this_month_revenue': self._get_revenue_amount(current_month_start, now),
            'this_year_revenue': self._get_revenue_amount(current_year_start, now),
            'outstanding_payments': self._get_outstanding_payments(),
            'revenue_by_category': self._get_revenue_by_category(current_year_start, now),
            'monthly_trend': self._get_monthly_revenue_trend(12),
            'top_clients': self._get_top_clients(current_year_start, now),
            'project_performance': self._get_project_performance(),
        }
        
        # 목표 대비 성과
        revenue_stats.update({
            'target_achievement': self._get_target_achievement(now),
        })
        
        revenue_stats['last_updated'] = timezone.now().isoformat()
        
        cache.set(cache_key, revenue_stats, self.cache_timeout)
        return revenue_stats
    
    def _get_user_info(self, user):
        """사용자 기본 정보"""
        return {
            'username': user.username,
            'full_name': user.get_full_name(),
            'user_type': user.user_type,
            'user_type_display': user.get_user_type_display(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
        }
    
    def _get_quick_stats(self, user):
        """빠른 통계"""
        today = timezone.now().date()
        
        # 공통 통계
        stats = {
            'today_events': CalendarEvent.objects.filter(
                Q(creator=user) | Q(attendees=user),
                start_datetime__date=today,
                is_active=True
            ).distinct().count(),
            'pending_tasks': 0,  # 향후 추가 예정
            'unread_notifications': self._get_unread_count(user),
        }
        
        # 권한별 추가 통계
        if user.user_type in ['SUPER_ADMIN', 'MANAGER']:
            stats.update({
                'active_projects': Project.objects.filter(
                    status='in_progress'
                ).count(),
                'monthly_revenue': self._get_current_month_revenue(),
            })
        
        return stats
    
    def _get_recent_activities(self, user):
        """최근 활동"""
        activities = []
        
        # 최근 캘린더 이벤트
        recent_events = CalendarEvent.objects.filter(
            Q(creator=user) | Q(attendees=user),
            is_active=True
        ).order_by('-updated_at')[:5]
        
        for event in recent_events:
            activities.append({
                'type': 'calendar_event',
                'title': f"캘린더: {event.title}",
                'description': f"{event.start_datetime.strftime('%m/%d %H:%M')}",
                'timestamp': event.updated_at.isoformat(),
                'icon': 'calendar',
                'url': f'/calendar/event/{event.id}/'
            })
        
        # 권한별 추가 활동
        if user.user_type in ['SUPER_ADMIN', 'MANAGER']:
            # 최근 매출 기록
            recent_revenues = RevenueRecord.objects.filter(
                is_confirmed=True
            ).order_by('-created_at')[:3]
            
            for revenue in recent_revenues:
                activities.append({
                    'type': 'revenue',
                    'title': f"매출: {revenue.project.name}",
                    'description': f"{revenue.amount:,}원",
                    'timestamp': revenue.created_at.isoformat(),
                    'icon': 'money',
                    'url': f'/revenue/record/{revenue.id}/'
                })
        
        return sorted(activities, key=lambda x: x['timestamp'], reverse=True)[:10]
    
    def _get_system_alerts(self, user):
        """시스템 알림"""
        alerts = []
        
        # 관리자만 시스템 알림 조회
        if user.user_type == 'SUPER_ADMIN':
            # 시스템 상태 경고
            critical_metrics = SystemHealthMetric.objects.filter(
                recorded_at__gte=timezone.now() - timedelta(minutes=30)
            ).exclude(
                critical_threshold__isnull=True
            ).filter(
                value__gte=F('critical_threshold')
            )
            
            for metric in critical_metrics:
                alerts.append({
                    'type': 'critical',
                    'title': f"시스템 경고: {metric.get_metric_type_display()}",
                    'message': f"{metric.value}{metric.unit}",
                    'timestamp': metric.recorded_at.isoformat()
                })
        
        return alerts
    
    def _get_revenue_summary(self, user):
        """매출 요약"""
        now = timezone.now()
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        return {
            'this_month': self._get_revenue_amount(this_month_start, now),
            'last_month': self._get_revenue_amount(
                (this_month_start - timedelta(days=1)).replace(day=1),
                this_month_start
            ),
            'outstanding': self._get_outstanding_payments(),
        }
    
    def _get_team_performance(self, user):
        """팀 성과"""
        # 활성 사용자 수
        active_users = CustomUser.objects.filter(
            is_active=True,
            last_login__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        return {
            'active_users': active_users,
            'total_users': CustomUser.objects.filter(is_active=True).count(),
        }
    
    def _get_pie_chart_data(self, data_source, user, time_range):
        """원형 차트 데이터"""
        if data_source == 'revenue':
            return self._get_revenue_category_pie_data(time_range)
        elif data_source == 'calendar':
            return self._get_calendar_type_pie_data(user, time_range)
        return {'data': [], 'labels': []}
    
    def _get_bar_chart_data(self, data_source, user, time_range):
        """막대 차트 데이터"""
        if data_source == 'revenue':
            return self._get_monthly_revenue_bars(time_range)
        return {'data': [], 'labels': []}
    
    def _get_line_chart_data(self, data_source, user, time_range):
        """선형 차트 데이터"""
        if data_source == 'revenue':
            return self._get_revenue_trend_line(time_range)
        return {'data': [], 'labels': []}
    
    def _get_stats_card_data(self, data_source, user, time_range):
        """통계 카드 데이터"""
        if data_source == 'revenue':
            return self._get_revenue_stats_card(time_range)
        elif data_source == 'calendar':
            return self._get_calendar_stats_card(user, time_range)
        return {'value': 0, 'label': '', 'change': 0}
    
    def _get_table_data(self, data_source, user, time_range):
        """테이블 데이터"""
        if data_source == 'revenue':
            return self._get_recent_revenue_table()
        elif data_source == 'calendar':
            return self._get_upcoming_events_table(user)
        return {'headers': [], 'rows': []}
    
    def _get_calendar_widget_data(self, user, time_range):
        """캘린더 위젯 데이터"""
        days = self._parse_time_range(time_range)
        start_date = timezone.now()
        end_date = start_date + timedelta(days=days)
        
        events = CalendarEvent.objects.filter(
            Q(creator=user) | Q(attendees=user),
            start_datetime__range=[start_date, end_date],
            is_active=True
        ).distinct()[:20]
        
        events_data = []
        for event in events:
            if event.can_view(user):
                events_data.append({
                    'id': event.id,
                    'title': event.title,
                    'start': event.start_datetime.isoformat(),
                    'end': event.end_datetime.isoformat(),
                    'color': event.category.color if event.category else '#3788d8',
                    'type': event.event_type,
                })
        
        return {'events': events_data}
    
    def _get_progress_data(self, data_source, user, time_range):
        """진행률 데이터"""
        if data_source == 'revenue':
            return self._get_revenue_target_progress()
        return {'current': 0, 'target': 100, 'percentage': 0}
    
    def _get_revenue_amount(self, start_date, end_date):
        """기간별 매출 금액"""
        total = RevenueRecord.objects.filter(
            revenue_date__range=[start_date, end_date],
            is_confirmed=True
        ).aggregate(
            total=Sum('net_amount')
        )['total'] or Decimal('0')
        
        return float(total)
    
    def _get_outstanding_payments(self):
        """미수금"""
        total = RevenueRecord.objects.filter(
            payment_status__in=['pending', 'overdue']
        ).aggregate(
            total=Sum('net_amount')
        )['total'] or Decimal('0')
        
        return float(total)
    
    def _get_revenue_by_category(self, start_date, end_date):
        """카테고리별 매출"""
        categories = RevenueRecord.objects.filter(
            revenue_date__range=[start_date, end_date],
            is_confirmed=True
        ).values(
            'category__name'
        ).annotate(
            total=Sum('net_amount')
        ).order_by('-total')[:10]
        
        return [
            {
                'category': item['category__name'] or '기타',
                'amount': float(item['total'])
            }
            for item in categories
        ]
    
    def _get_monthly_revenue_trend(self, months=12):
        """월별 매출 트렌드"""
        end_date = timezone.now()
        trends = []
        
        for i in range(months):
            month_start = (end_date.replace(day=1) - timedelta(days=i*30)).replace(day=1)
            month_end = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            
            amount = self._get_revenue_amount(month_start, month_end)
            trends.append({
                'month': month_start.strftime('%Y-%m'),
                'amount': amount
            })
        
        return list(reversed(trends))
    
    def _get_top_clients(self, start_date, end_date):
        """주요 고객"""
        clients = RevenueRecord.objects.filter(
            revenue_date__range=[start_date, end_date],
            is_confirmed=True
        ).values(
            'client__name'
        ).annotate(
            total=Sum('net_amount'),
            count=Count('id')
        ).order_by('-total')[:10]
        
        return [
            {
                'client': item['client__name'],
                'amount': float(item['total']),
                'projects': item['count']
            }
            for item in clients
        ]
    
    def _get_project_performance(self):
        """프로젝트 성과"""
        projects = Project.objects.filter(
            status='in_progress'
        ).annotate(
            revenue_sum=Sum('revenue_records__net_amount', 
                          filter=Q(revenue_records__is_confirmed=True))
        )
        
        performance = []
        for project in projects[:10]:
            completion_rate = project.completion_rate if hasattr(project, 'completion_rate') else 0
            performance.append({
                'name': project.name,
                'completion_rate': completion_rate,
                'revenue': float(project.revenue_sum or 0),
                'target': float(project.contract_amount)
            })
        
        return performance
    
    def _get_target_achievement(self, now):
        """목표 달성률"""
        # 현재 월 목표
        monthly_target = RevenueTarget.objects.filter(
            target_type='monthly',
            year=now.year,
            month=now.month
        ).first()
        
        if monthly_target:
            achievement = monthly_target.get_achievement_rate()
            return {
                'type': 'monthly',
                'target': float(monthly_target.target_amount),
                'current': float(monthly_target.target_amount * achievement / 100),
                'rate': achievement
            }
        
        return {'type': 'monthly', 'target': 0, 'current': 0, 'rate': 0}
    
    def _get_current_month_revenue(self):
        """현재 월 매출"""
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return self._get_revenue_amount(month_start, now)
    
    def _get_unread_count(self, user):
        """읽지 않은 알림 수"""
        all_notifications = DashboardNotification.objects.filter(
            Q(target_users=user) | Q(target_user_types__contains=[user.user_type]),
            is_active=True
        )
        
        read_notification_ids = NotificationReadStatus.objects.filter(
            user=user,
            is_read=True
        ).values_list('notification_id', flat=True)
        
        return all_notifications.exclude(id__in=read_notification_ids).count()
    
    def _parse_time_range(self, time_range):
        """시간 범위 파싱"""
        if time_range.endswith('d'):
            return int(time_range[:-1])
        elif time_range.endswith('w'):
            return int(time_range[:-1]) * 7
        elif time_range.endswith('m'):
            return int(time_range[:-1]) * 30
        return 7


class NotificationService:
    """알림 서비스"""
    
    def create_notification(self, title, message, notification_type='info', 
                          target_users=None, target_user_types=None, **kwargs):
        """알림 생성"""
        
        notification = DashboardNotification.objects.create(
            title=title,
            message=message,
            notification_type=notification_type,
            target_user_types=target_user_types or [],
            **kwargs
        )
        
        if target_users:
            notification.target_users.set(target_users)
        
        return notification
    
    def send_revenue_alert(self, revenue_record):
        """매출 알림 발송"""
        if revenue_record.amount >= 10000000:  # 1천만원 이상
            self.create_notification(
                title="대형 매출 발생",
                message=f"{revenue_record.project.name}: {revenue_record.amount:,}원",
                notification_type="success",
                target_user_types=['SUPER_ADMIN', 'MANAGER']
            )
    
    def send_system_alert(self, metric_type, value, threshold):
        """시스템 경고 발송"""
        self.create_notification(
            title=f"시스템 경고: {metric_type}",
            message=f"임계값({threshold}) 초과: {value}",
            notification_type="warning",
            target_user_types=['SUPER_ADMIN'],
            priority="high"
        )


class CacheManager:
    """캐시 관리자"""
    
    @staticmethod
    def invalidate_dashboard_cache(user_id=None, user_type=None):
        """대시보드 캐시 무효화"""
        if user_id:
            cache_patterns = [
                f"dashboard_overview_{user_id}_*",
                f"widget_*_{user_id}_*",
                f"revenue_dashboard_{user_id}",
            ]
            
            for pattern in cache_patterns:
                cache.delete_pattern(pattern)
    
    @staticmethod
    def warm_dashboard_cache(user):
        """대시보드 캐시 워밍"""
        service = DashboardDataService()
        service.get_dashboard_overview(user)
        
        if user.user_type in ['SUPER_ADMIN', 'MANAGER']:
            service.get_revenue_dashboard_data(user)