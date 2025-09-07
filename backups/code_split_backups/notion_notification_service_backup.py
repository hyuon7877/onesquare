"""
OneSquare Dashboard - Notion 기반 알림 시스템
Notion 데이터베이스 변경사항을 감지하고 실시간 알림 생성
"""

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q
import json
import logging
from datetime import timedelta
from typing import List, Dict, Optional, Any

from .models import DashboardNotification, NotificationReadStatus
from apps.notion_api.models import NotionPage, SyncHistory, NotionDatabase
from apps.notion_api.services import NotionSyncService as NotionAPIService
from apps.auth_system.models import CustomUser

logger = logging.getLogger(__name__)
User = get_user_model()


class NotionNotificationService:
    """Notion 기반 알림 서비스"""
    
    def __init__(self):
        self.notion_service = NotionAPIService()
        self.notification_rules = self._load_notification_rules()
    
    def _load_notification_rules(self) -> Dict[str, Any]:
        """알림 규칙 설정"""
        return {
            'revenue_changes': {
                'priority': 'high',
                'target_user_types': ['SUPER_ADMIN', 'MANAGER'],
                'notification_type': 'warning',
                'threshold': 1000000  # 100만원 이상 변경시 알림
            },
            'project_updates': {
                'priority': 'medium',
                'target_user_types': ['SUPER_ADMIN', 'MANAGER', 'TEAM_MEMBER'],
                'notification_type': 'info'
            },
            'urgent_tasks': {
                'priority': 'critical',
                'target_user_types': ['SUPER_ADMIN', 'MANAGER', 'TEAM_MEMBER'],
                'notification_type': 'urgent'
            },
            'partner_reports': {
                'priority': 'medium',
                'target_user_types': ['SUPER_ADMIN', 'MANAGER'],
                'notification_type': 'info'
            },
            'system_errors': {
                'priority': 'critical',
                'target_user_types': ['SUPER_ADMIN'],
                'notification_type': 'error'
            }
        }
    
    def check_notion_changes(self) -> List[DashboardNotification]:
        """Notion 변경사항 확인 및 알림 생성"""
        notifications = []
        
        try:
            # 최근 동기화 기록 확인
            recent_syncs = SyncHistory.objects.filter(
                completed_at__gte=timezone.now() - timedelta(hours=1),
                status=SyncHistory.SyncStatus.COMPLETED
            ).order_by('-completed_at')
            
            for sync in recent_syncs:
                # 각 동기화에 대해 알림 생성 확인
                sync_notifications = self._analyze_sync_changes(sync)
                notifications.extend(sync_notifications)
            
            # Notion 페이지 직접 변경사항 확인
            page_notifications = self._check_page_changes()
            notifications.extend(page_notifications)
            
            logger.info(f"Generated {len(notifications)} notifications from Notion changes")
            
        except Exception as e:
            logger.error(f"Error checking Notion changes: {e}")
            # 시스템 오류 알림 생성
            error_notification = self._create_system_error_notification(str(e))
            notifications.append(error_notification)
        
        return notifications
    
    def _analyze_sync_changes(self, sync: SyncHistory) -> List[DashboardNotification]:
        """동기화 결과 분석 및 알림 생성"""
        notifications = []
        
        # 매출 관련 변경사항
        if sync.database.database_type == 'projects' and sync.pages_updated > 0:
            revenue_notification = self._create_revenue_change_notification(sync)
            if revenue_notification:
                notifications.append(revenue_notification)
        
        # 프로젝트 업데이트
        if sync.database.database_type == 'projects' and (sync.pages_created > 0 or sync.pages_updated > 0):
            project_notification = self._create_project_update_notification(sync)
            notifications.append(project_notification)
        
        # 파트너 리포트
        if sync.database.database_type == 'reports' and sync.pages_created > 0:
            report_notification = self._create_partner_report_notification(sync)
            notifications.append(report_notification)
        
        # 동기화 실패 알림
        if sync.pages_failed > 0:
            error_notification = self._create_sync_error_notification(sync)
            notifications.append(error_notification)
        
        return notifications
    
    def _check_page_changes(self) -> List[DashboardNotification]:
        """최근 페이지 변경사항 확인"""
        notifications = []
        
        # 최근 1시간 내 변경된 페이지
        recent_pages = NotionPage.objects.filter(
            updated_at__gte=timezone.now() - timedelta(hours=1),
            is_dirty=True
        ).select_related('database')
        
        # 긴급 작업 확인
        for page in recent_pages:
            if self._is_urgent_task(page):
                urgent_notification = self._create_urgent_task_notification(page)
                notifications.append(urgent_notification)
        
        return notifications
    
    def _is_urgent_task(self, page: NotionPage) -> bool:
        """긴급 작업 여부 판단"""
        try:
            properties = page.properties or {}
            
            # 우선순위가 '긴급'인 경우
            priority = properties.get('우선순위', {}).get('select', {}).get('name', '')
            if priority == '긴급':
                return True
            
            # 마감일이 오늘인 경우
            due_date = properties.get('마감일', {}).get('date', {})
            if due_date and due_date.get('start'):
                due_date_str = due_date['start']
                if due_date_str == timezone.now().date().isoformat():
                    return True
            
            # 상태가 '블로킹'인 경우
            status = properties.get('상태', {}).get('select', {}).get('name', '')
            if status in ['블로킹', '긴급', '위험']:
                return True
                
        except Exception as e:
            logger.error(f"Error checking urgent task: {e}")
        
        return False
    
    def _create_revenue_change_notification(self, sync: SyncHistory) -> Optional[DashboardNotification]:
        """매출 변경 알림 생성"""
        rule = self.notification_rules['revenue_changes']
        
        # 큰 변경사항만 알림 생성 (임계값 기반)
        if sync.pages_updated >= 5:  # 5개 이상 페이지 업데이트시
            notification = DashboardNotification.objects.create(
                title=f"매출 데이터 업데이트",
                message=f"{sync.pages_updated}개의 매출 관련 항목이 업데이트되었습니다.",
                notification_type=rule['notification_type'],
                priority=rule['priority'],
                source_type='notion_sync',
                source_id=str(sync.sync_id),
                metadata={
                    'sync_id': str(sync.sync_id),
                    'database_id': str(sync.database.notion_id),
                    'pages_updated': sync.pages_updated,
                    'timestamp': timezone.now().isoformat()
                }
            )
            
            # 대상 사용자 설정
            self._set_notification_targets(notification, rule['target_user_types'])
            return notification
        
        return None
    
    def _create_project_update_notification(self, sync: SyncHistory) -> DashboardNotification:
        """프로젝트 업데이트 알림 생성"""
        rule = self.notification_rules['project_updates']
        
        message_parts = []
        if sync.pages_created > 0:
            message_parts.append(f"새 프로젝트 {sync.pages_created}개 생성")
        if sync.pages_updated > 0:
            message_parts.append(f"프로젝트 {sync.pages_updated}개 업데이트")
        
        notification = DashboardNotification.objects.create(
            title="프로젝트 현황 업데이트",
            message=", ".join(message_parts),
            notification_type=rule['notification_type'],
            priority=rule['priority'],
            source_type='notion_sync',
            source_id=str(sync.sync_id),
            metadata={
                'sync_id': str(sync.sync_id),
                'database_type': sync.database.database_type,
                'pages_created': sync.pages_created,
                'pages_updated': sync.pages_updated,
                'timestamp': timezone.now().isoformat()
            }
        )
        
        self._set_notification_targets(notification, rule['target_user_types'])
        return notification
    
    def _create_partner_report_notification(self, sync: SyncHistory) -> DashboardNotification:
        """파트너 리포트 알림 생성"""
        rule = self.notification_rules['partner_reports']
        
        notification = DashboardNotification.objects.create(
            title="새로운 현장 리포트",
            message=f"{sync.pages_created}개의 새로운 현장 리포트가 등록되었습니다.",
            notification_type=rule['notification_type'],
            priority=rule['priority'],
            source_type='notion_sync',
            source_id=str(sync.sync_id),
            metadata={
                'sync_id': str(sync.sync_id),
                'new_reports': sync.pages_created,
                'timestamp': timezone.now().isoformat()
            }
        )
        
        self._set_notification_targets(notification, rule['target_user_types'])
        return notification
    
    def _create_urgent_task_notification(self, page: NotionPage) -> DashboardNotification:
        """긴급 작업 알림 생성"""
        rule = self.notification_rules['urgent_tasks']
        
        notification = DashboardNotification.objects.create(
            title="긴급 작업 알림",
            message=f"긴급 작업이 업데이트되었습니다: {page.title}",
            notification_type=rule['notification_type'],
            priority=rule['priority'],
            source_type='notion_page',
            source_id=page.notion_id,
            action_url=f"/dashboard/?page={page.notion_id}",
            metadata={
                'page_id': page.notion_id,
                'page_title': page.title,
                'database_type': page.database.database_type,
                'timestamp': timezone.now().isoformat()
            }
        )
        
        self._set_notification_targets(notification, rule['target_user_types'])
        return notification
    
    def _create_sync_error_notification(self, sync: SyncHistory) -> DashboardNotification:
        """동기화 오류 알림 생성"""
        rule = self.notification_rules['system_errors']
        
        notification = DashboardNotification.objects.create(
            title="Notion 동기화 오류",
            message=f"{sync.pages_failed}개 페이지 동기화에 실패했습니다. 확인이 필요합니다.",
            notification_type=rule['notification_type'],
            priority=rule['priority'],
            source_type='sync_error',
            source_id=str(sync.sync_id),
            action_url="/admin/notion_api/synchistory/",
            metadata={
                'sync_id': str(sync.sync_id),
                'failed_pages': sync.pages_failed,
                'error_message': sync.error_message,
                'timestamp': timezone.now().isoformat()
            }
        )
        
        self._set_notification_targets(notification, rule['target_user_types'])
        return notification
    
    def _create_system_error_notification(self, error_message: str) -> DashboardNotification:
        """시스템 오류 알림 생성"""
        rule = self.notification_rules['system_errors']
        
        notification = DashboardNotification.objects.create(
            title="시스템 오류 발생",
            message=f"Notion 알림 시스템에서 오류가 발생했습니다: {error_message[:100]}...",
            notification_type=rule['notification_type'],
            priority=rule['priority'],
            source_type='system_error',
            source_id='notification_service',
            metadata={
                'error_message': error_message,
                'component': 'NotionNotificationService',
                'timestamp': timezone.now().isoformat()
            }
        )
        
        self._set_notification_targets(notification, rule['target_user_types'])
        return notification
    
    def _set_notification_targets(self, notification: DashboardNotification, target_user_types: List[str]):
        """알림 대상 사용자 설정"""
        notification.target_user_types = target_user_types
        notification.save()
        
        # 해당 사용자 타입의 활성 사용자들을 대상으로 설정
        target_users = CustomUser.objects.filter(
            user_type__in=target_user_types,
            is_active=True
        )
        
        notification.target_users.set(target_users)
    
    def get_user_notifications(self, user: User, limit: int = 50) -> List[Dict]:
        """사용자별 알림 목록 조회"""
        notifications = DashboardNotification.objects.filter(
            Q(target_users=user) | Q(target_user_types__contains=[user.user_type])
        ).select_related().prefetch_related(
            'read_status'
        ).order_by('-created_at')[:limit]
        
        result = []
        for notification in notifications:
            try:
                read_status = notification.read_status.get(user=user)
                is_read = read_status.is_read
                read_at = read_status.read_at
            except NotificationReadStatus.DoesNotExist:
                is_read = False
                read_at = None
            
            result.append({
                'id': str(notification.id),
                'title': notification.title,
                'message': notification.message,
                'type': notification.notification_type,
                'priority': notification.priority,
                'created_at': notification.created_at,
                'is_read': is_read,
                'read_at': read_at,
                'action_url': notification.action_url,
                'metadata': notification.metadata
            })
        
        return result
    
    def mark_notification_read(self, user: User, notification_id: str) -> bool:
        """알림 읽음 처리"""
        try:
            notification = DashboardNotification.objects.get(id=notification_id)
            read_status, created = NotificationReadStatus.objects.get_or_create(
                notification=notification,
                user=user,
                defaults={'is_read': True, 'read_at': timezone.now()}
            )
            
            if not created and not read_status.is_read:
                read_status.is_read = True
                read_status.read_at = timezone.now()
                read_status.save()
            
            return True
            
        except DashboardNotification.DoesNotExist:
            logger.error(f"Notification not found: {notification_id}")
            return False
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            return False
    
    def get_notification_stats(self, user: User) -> Dict[str, int]:
        """사용자 알림 통계"""
        user_notifications = DashboardNotification.objects.filter(
            Q(target_users=user) | Q(target_user_types__contains=[user.user_type])
        )
        
        total = user_notifications.count()
        
        # 읽지 않은 알림 수
        read_notification_ids = NotificationReadStatus.objects.filter(
            user=user,
            is_read=True
        ).values_list('notification_id', flat=True)
        
        unread = user_notifications.exclude(id__in=read_notification_ids).count()
        
        # 우선순위별 통계
        critical = user_notifications.filter(priority='critical').count()
        high = user_notifications.filter(priority='high').count()
        
        return {
            'total': total,
            'unread': unread,
            'critical': critical,
            'high': high
        }
    
    def cleanup_old_notifications(self, days: int = 30):
        """오래된 알림 정리"""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # 30일 이상 된 읽음 상태의 일반 알림 삭제
        old_notifications = DashboardNotification.objects.filter(
            created_at__lt=cutoff_date,
            priority__in=['low', 'medium']
        )
        
        # 읽은 알림만 삭제
        read_notification_ids = NotificationReadStatus.objects.filter(
            notification__in=old_notifications,
            is_read=True
        ).values_list('notification_id', flat=True)
        
        deleted_count = DashboardNotification.objects.filter(
            id__in=read_notification_ids
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old notifications")
        return deleted_count


class NotionChangePoller:
    """Notion 변경사항 주기적 체크 서비스"""
    
    def __init__(self):
        self.notification_service = NotionNotificationService()
        self.notion_service = NotionAPIService()
    
    def run_polling_cycle(self):
        """폴링 주기 실행"""
        logger.info("Starting Notion change polling cycle...")
        
        try:
            # 1. 각 데이터베이스별 동기화 실행
            databases = NotionDatabase.objects.filter(is_active=True)
            
            for database in databases:
                self._sync_database(database)
            
            # 2. 변경사항 기반 알림 생성
            notifications = self.notification_service.check_notion_changes()
            
            logger.info(f"Polling cycle completed. Generated {len(notifications)} notifications.")
            
        except Exception as e:
            logger.error(f"Error in polling cycle: {e}")
            # 시스템 오류 알림 생성
            self.notification_service._create_system_error_notification(str(e))
    
    def _sync_database(self, database: NotionDatabase):
        """개별 데이터베이스 동기화"""
        try:
            # 마지막 동기화 이후 변경된 페이지만 확인
            last_sync = SyncHistory.objects.filter(
                database=database,
                status=SyncHistory.SyncStatus.COMPLETED
            ).order_by('-completed_at').first()
            
            since = last_sync.completed_at if last_sync else timezone.now() - timedelta(hours=24)
            
            # Notion API를 통한 변경사항 확인
            changes = self.notion_service.get_database_changes(
                database.notion_id,
                since=since
            )
            
            if changes:
                logger.info(f"Found {len(changes)} changes in database {database.title}")
                # 동기화 수행 및 기록
                self.notion_service.sync_database_pages(database, changes)
            
        except Exception as e:
            logger.error(f"Error syncing database {database.title}: {e}")