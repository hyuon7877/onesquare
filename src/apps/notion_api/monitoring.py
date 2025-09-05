"""
OneSquare Notion API 연동 - 모니터링 시스템

Notion API 동기화 상태 모니터링 및 알림 시스템
"""

import logging
import smtplib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.core.mail import send_mail
from django.db.models import Count, Q, Avg
from django.template.loader import render_to_string

from .models import NotionDatabase, SyncHistory, NotionPage


logger = logging.getLogger(__name__)


class NotionSyncMonitor:
    """Notion 동기화 모니터링"""
    
    def __init__(self):
        self.alert_threshold_minutes = getattr(settings, 'NOTION_ALERT_THRESHOLD_MINUTES', 30)
        self.max_failed_syncs = getattr(settings, 'NOTION_MAX_FAILED_SYNCS', 3)
        self.admin_emails = getattr(settings, 'NOTION_ADMIN_EMAILS', [])
    
    def check_sync_health(self) -> Dict[str, Any]:
        """동기화 상태 건강성 검사"""
        now = timezone.now()
        
        health_report = {
            'timestamp': now.isoformat(),
            'overall_status': 'healthy',
            'issues': [],
            'warnings': [],
            'databases_status': [],
            'statistics': {}
        }
        
        # 활성 데이터베이스별 검사
        active_databases = NotionDatabase.objects.filter(is_active=True)
        
        for database in active_databases:
            db_health = self._check_database_health(database, now)
            health_report['databases_status'].append(db_health)
            
            # 문제가 있는 경우 전체 상태 업데이트
            if db_health['status'] == 'critical':
                health_report['overall_status'] = 'critical'
                health_report['issues'].append(db_health['message'])
            elif db_health['status'] == 'warning':
                if health_report['overall_status'] == 'healthy':
                    health_report['overall_status'] = 'warning'
                health_report['warnings'].append(db_health['message'])
        
        # 전체 통계 계산
        health_report['statistics'] = self._calculate_sync_statistics(now)
        
        # 문제가 있으면 알림 발송
        if health_report['overall_status'] in ['critical', 'warning']:
            self._send_health_alert(health_report)
        
        return health_report
    
    def _check_database_health(self, database: NotionDatabase, now: datetime) -> Dict[str, Any]:
        """개별 데이터베이스 건강성 검사"""
        db_status = {
            'database_id': database.id,
            'database_title': database.title,
            'status': 'healthy',
            'message': '',
            'last_sync_time': None,
            'sync_overdue_minutes': 0,
            'recent_failures': 0,
            'success_rate_24h': 100.0
        }
        
        # 마지막 동기화 시간 확인
        if database.last_synced:
            db_status['last_sync_time'] = database.last_synced.isoformat()
            time_since_sync = now - database.last_synced
            sync_interval = timedelta(seconds=database.sync_interval)
            
            # 동기화 지연 확인
            if time_since_sync > sync_interval * 1.5:
                overdue_minutes = (time_since_sync - sync_interval).total_seconds() / 60
                db_status['sync_overdue_minutes'] = int(overdue_minutes)
                
                if overdue_minutes > self.alert_threshold_minutes:
                    db_status['status'] = 'critical'
                    db_status['message'] = f"동기화가 {int(overdue_minutes)}분 지연됨"
                else:
                    db_status['status'] = 'warning'
                    db_status['message'] = f"동기화가 {int(overdue_minutes)}분 지연됨"
        else:
            db_status['status'] = 'critical'
            db_status['message'] = "동기화된 적이 없음"
        
        # 최근 실패 횟수 확인
        recent_syncs = SyncHistory.objects.filter(
            database=database,
            started_at__gte=now - timedelta(hours=24)
        )
        
        if recent_syncs.exists():
            failed_syncs = recent_syncs.filter(status='failed')
            db_status['recent_failures'] = failed_syncs.count()
            
            # 성공률 계산
            total_syncs = recent_syncs.count()
            successful_syncs = recent_syncs.filter(status='completed').count()
            db_status['success_rate_24h'] = (successful_syncs / total_syncs) * 100
            
            # 연속 실패 확인
            if db_status['recent_failures'] >= self.max_failed_syncs:
                db_status['status'] = 'critical'
                if db_status['message']:
                    db_status['message'] += f", 최근 {db_status['recent_failures']}회 연속 실패"
                else:
                    db_status['message'] = f"최근 {db_status['recent_failures']}회 연속 실패"
            elif db_status['success_rate_24h'] < 80:
                if db_status['status'] == 'healthy':
                    db_status['status'] = 'warning'
                if db_status['message']:
                    db_status['message'] += f", 성공률 {db_status['success_rate_24h']:.1f}%"
                else:
                    db_status['message'] = f"성공률이 낮음 ({db_status['success_rate_24h']:.1f}%)"
        
        return db_status
    
    def _calculate_sync_statistics(self, now: datetime) -> Dict[str, Any]:
        """동기화 통계 계산"""
        stats = {
            'active_databases': 0,
            'total_syncs_24h': 0,
            'successful_syncs_24h': 0,
            'failed_syncs_24h': 0,
            'avg_sync_duration': 0,
            'total_pages_synced': 0,
            'overall_success_rate': 100.0
        }
        
        # 활성 데이터베이스 수
        stats['active_databases'] = NotionDatabase.objects.filter(is_active=True).count()
        
        # 최근 24시간 동기화 통계
        recent_syncs = SyncHistory.objects.filter(
            started_at__gte=now - timedelta(hours=24)
        )
        
        if recent_syncs.exists():
            stats['total_syncs_24h'] = recent_syncs.count()
            stats['successful_syncs_24h'] = recent_syncs.filter(status='completed').count()
            stats['failed_syncs_24h'] = recent_syncs.filter(status='failed').count()
            
            # 성공률 계산
            if stats['total_syncs_24h'] > 0:
                stats['overall_success_rate'] = (stats['successful_syncs_24h'] / stats['total_syncs_24h']) * 100
            
            # 평균 동기화 시간
            completed_syncs = recent_syncs.filter(
                status='completed',
                duration__isnull=False
            )
            if completed_syncs.exists():
                avg_duration = completed_syncs.aggregate(avg_duration=Avg('duration'))['avg_duration']
                if avg_duration:
                    stats['avg_sync_duration'] = avg_duration.total_seconds()
            
            # 총 동기화된 페이지 수
            stats['total_pages_synced'] = sum(
                sync.total_pages for sync in recent_syncs if sync.total_pages
            )
        
        return stats
    
    def _send_health_alert(self, health_report: Dict[str, Any]):
        """건강성 검사 결과 알림 발송"""
        if not self.admin_emails:
            logger.warning("관리자 이메일이 설정되지 않아 알림을 발송할 수 없습니다")
            return
        
        # 동일한 알림의 중복 발송 방지
        alert_key = f"notion_health_alert_{health_report['overall_status']}"
        if cache.get(alert_key):
            return
        
        # 1시간 동안 동일한 레벨의 알림 발송 방지
        cache.set(alert_key, True, 3600)
        
        try:
            subject = f"[OneSquare] Notion 동기화 {health_report['overall_status'].upper()} 알림"
            
            # 이메일 본문 생성
            email_context = {
                'health_report': health_report,
                'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            message = self._format_health_alert_message(email_context)
            
            # 이메일 발송
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=self.admin_emails,
                fail_silently=False
            )
            
            logger.info(f"건강성 검사 알림 발송 완료: {health_report['overall_status']}")
            
        except Exception as e:
            logger.error(f"건강성 검사 알림 발송 실패: {str(e)}")
    
    def _format_health_alert_message(self, context: Dict[str, Any]) -> str:
        """알림 메시지 포맷팅"""
        health_report = context['health_report']
        timestamp = context['timestamp']
        
        message_lines = [
            f"OneSquare Notion 동기화 상태 리포트",
            f"시간: {timestamp}",
            f"전체 상태: {health_report['overall_status'].upper()}",
            "",
        ]
        
        # 문제 사항
        if health_report['issues']:
            message_lines.append("🚨 긴급 문제:")
            for issue in health_report['issues']:
                message_lines.append(f"  - {issue}")
            message_lines.append("")
        
        # 경고 사항
        if health_report['warnings']:
            message_lines.append("⚠️ 경고 사항:")
            for warning in health_report['warnings']:
                message_lines.append(f"  - {warning}")
            message_lines.append("")
        
        # 통계
        stats = health_report['statistics']
        message_lines.extend([
            "📊 통계 (최근 24시간):",
            f"  활성 데이터베이스: {stats['active_databases']}개",
            f"  총 동기화: {stats['total_syncs_24h']}회",
            f"  성공: {stats['successful_syncs_24h']}회",
            f"  실패: {stats['failed_syncs_24h']}회",
            f"  전체 성공률: {stats['overall_success_rate']:.1f}%",
            f"  평균 소요시간: {stats['avg_sync_duration']:.1f}초",
            f"  처리된 페이지: {stats['total_pages_synced']}개",
            "",
        ])
        
        # 데이터베이스별 상태
        if health_report['databases_status']:
            message_lines.append("📋 데이터베이스별 상태:")
            for db_status in health_report['databases_status']:
                status_icon = {"healthy": "✅", "warning": "⚠️", "critical": "🚨"}
                icon = status_icon.get(db_status['status'], "❓")
                
                message_lines.append(
                    f"  {icon} {db_status['database_title']}: "
                    f"{db_status['status']}"
                )
                
                if db_status['message']:
                    message_lines.append(f"     문제: {db_status['message']}")
                
                if db_status['success_rate_24h'] < 100:
                    message_lines.append(
                        f"     24시간 성공률: {db_status['success_rate_24h']:.1f}%"
                    )
        
        return "\n".join(message_lines)
    
    def get_performance_metrics(self, days: int = 7) -> Dict[str, Any]:
        """성능 메트릭 수집"""
        now = timezone.now()
        start_date = now - timedelta(days=days)
        
        metrics = {
            'period_days': days,
            'start_date': start_date.isoformat(),
            'end_date': now.isoformat(),
            'daily_stats': [],
            'database_performance': [],
            'trend_analysis': {}
        }
        
        # 일별 통계
        for i in range(days):
            day_start = start_date + timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            
            day_syncs = SyncHistory.objects.filter(
                started_at__gte=day_start,
                started_at__lt=day_end
            )
            
            daily_stat = {
                'date': day_start.strftime('%Y-%m-%d'),
                'total_syncs': day_syncs.count(),
                'successful_syncs': day_syncs.filter(status='completed').count(),
                'failed_syncs': day_syncs.filter(status='failed').count(),
                'total_pages': sum(sync.total_pages or 0 for sync in day_syncs),
                'avg_duration': 0
            }
            
            # 평균 소요시간
            completed_syncs = day_syncs.filter(status='completed', duration__isnull=False)
            if completed_syncs.exists():
                avg_duration = completed_syncs.aggregate(avg_duration=Avg('duration'))['avg_duration']
                if avg_duration:
                    daily_stat['avg_duration'] = avg_duration.total_seconds()
            
            metrics['daily_stats'].append(daily_stat)
        
        # 데이터베이스별 성능
        active_databases = NotionDatabase.objects.filter(is_active=True)
        for database in active_databases:
            db_syncs = SyncHistory.objects.filter(
                database=database,
                started_at__gte=start_date
            )
            
            if db_syncs.exists():
                db_perf = {
                    'database_id': database.id,
                    'database_title': database.title,
                    'total_syncs': db_syncs.count(),
                    'success_rate': (db_syncs.filter(status='completed').count() / db_syncs.count()) * 100,
                    'avg_pages_per_sync': db_syncs.aggregate(avg_pages=Avg('total_pages'))['avg_pages'] or 0,
                    'total_pages_synced': sum(sync.total_pages or 0 for sync in db_syncs)
                }
                
                metrics['database_performance'].append(db_perf)
        
        # 트렌드 분석
        if len(metrics['daily_stats']) >= 3:
            recent_days = metrics['daily_stats'][-3:]
            earlier_days = metrics['daily_stats'][:-3] if len(metrics['daily_stats']) > 3 else []
            
            recent_avg_success = sum(day['successful_syncs'] for day in recent_days) / len(recent_days)
            
            if earlier_days:
                earlier_avg_success = sum(day['successful_syncs'] for day in earlier_days) / len(earlier_days)
                trend = "improving" if recent_avg_success > earlier_avg_success else "declining"
            else:
                trend = "stable"
            
            metrics['trend_analysis'] = {
                'sync_trend': trend,
                'recent_avg_success_rate': recent_avg_success,
                'performance_indicator': self._calculate_performance_indicator(metrics['daily_stats'])
            }
        
        return metrics
    
    def _calculate_performance_indicator(self, daily_stats: List[Dict]) -> str:
        """성능 지표 계산"""
        if not daily_stats:
            return "unknown"
        
        # 최근 3일 평균 성공률
        recent_days = daily_stats[-3:]
        total_syncs = sum(day['total_syncs'] for day in recent_days)
        successful_syncs = sum(day['successful_syncs'] for day in recent_days)
        
        if total_syncs == 0:
            return "no_activity"
        
        success_rate = (successful_syncs / total_syncs) * 100
        
        if success_rate >= 95:
            return "excellent"
        elif success_rate >= 90:
            return "good"
        elif success_rate >= 80:
            return "fair"
        else:
            return "poor"


# 모니터 인스턴스
sync_monitor = NotionSyncMonitor()


def run_health_check():
    """건강성 검사 실행 (외부 스케줄러용)"""
    return sync_monitor.check_sync_health()


def get_sync_metrics(days: int = 7):
    """성능 메트릭 조회"""
    return sync_monitor.get_performance_metrics(days)