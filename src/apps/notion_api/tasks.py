"""
OneSquare Notion API 연동 - 비동기 작업 정의

이 모듈은 Notion API 동기화를 위한 비동기 작업들을 정의합니다.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q

from .models import NotionDatabase, SyncHistory
from .services import NotionSyncService


logger = logging.getLogger(__name__)


class NotionSyncScheduler:
    """Notion 동기화 스케줄러"""
    
    def __init__(self):
        self.sync_service = NotionSyncService()
        self.cache_timeout = getattr(settings, 'NOTION_CACHE_TIMEOUT', 300)
    
    def run_scheduled_sync(self) -> Dict[str, Any]:
        """예정된 모든 데이터베이스 동기화 실행"""
        results = {
            'total_databases': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'skipped_syncs': 0,
            'sync_details': []
        }
        
        # 동기화가 필요한 활성 데이터베이스 조회
        databases_to_sync = self._get_databases_for_sync()
        results['total_databases'] = len(databases_to_sync)
        
        logger.info(f"시작: 예정된 동기화 - {results['total_databases']}개 데이터베이스")
        
        for database in databases_to_sync:
            try:
                sync_result = self._sync_single_database(database)
                results['sync_details'].append(sync_result)
                
                if sync_result['success']:
                    results['successful_syncs'] += 1
                elif sync_result['skipped']:
                    results['skipped_syncs'] += 1
                else:
                    results['failed_syncs'] += 1
                    
            except Exception as e:
                logger.error(f"데이터베이스 {database.title} 동기화 중 예외 발생: {str(e)}")
                results['failed_syncs'] += 1
                results['sync_details'].append({
                    'database_id': database.id,
                    'database_title': database.title,
                    'success': False,
                    'skipped': False,
                    'error': str(e)
                })
        
        logger.info(f"완료: 예정된 동기화 - 성공: {results['successful_syncs']}, "
                   f"실패: {results['failed_syncs']}, 스킵: {results['skipped_syncs']}")
        
        return results
    
    def _get_databases_for_sync(self) -> list:
        """동기화가 필요한 데이터베이스 목록 반환"""
        now = timezone.now()
        
        # 동기화 조건:
        # 1. 활성 상태
        # 2. 마지막 동기화가 sync_interval 이상 지남
        # 3. 현재 진행 중인 동기화가 없음
        databases = NotionDatabase.objects.filter(
            is_active=True
        ).exclude(
            # 진행 중인 동기화가 있는 데이터베이스 제외
            sync_history__status__in=['started', 'in_progress'],
            sync_history__started_at__gte=now - timedelta(hours=1)  # 1시간 이상 진행된 것은 오류로 간주
        )
        
        sync_needed = []
        for db in databases:
            if self._should_sync_database(db, now):
                sync_needed.append(db)
        
        return sync_needed
    
    def _should_sync_database(self, database: NotionDatabase, now: datetime) -> bool:
        """데이터베이스가 동기화가 필요한지 확인"""
        # 마지막 동기화 시간 확인
        if not database.last_synced:
            return True
        
        time_since_sync = now - database.last_synced
        sync_interval = timedelta(seconds=database.sync_interval)
        
        if time_since_sync >= sync_interval:
            return True
        
        # 강제 동기화 플래그 확인 (캐시)
        force_sync_key = f"notion_force_sync_{database.id}"
        if cache.get(force_sync_key):
            cache.delete(force_sync_key)
            return True
        
        return False
    
    def _sync_single_database(self, database: NotionDatabase) -> Dict[str, Any]:
        """단일 데이터베이스 동기화"""
        result = {
            'database_id': database.id,
            'database_title': database.title,
            'success': False,
            'skipped': False,
            'sync_id': None,
            'pages_processed': 0,
            'error': None
        }
        
        try:
            # 동기화 중복 실행 방지를 위한 락
            lock_key = f"notion_sync_lock_{database.id}"
            if cache.get(lock_key):
                result['skipped'] = True
                result['error'] = "동기화가 이미 진행 중입니다"
                return result
            
            # 락 설정 (5분 타임아웃)
            cache.set(lock_key, True, 300)
            
            try:
                # 증분 동기화 실행
                sync_result = self.sync_service.sync_database(
                    database=database,
                    sync_type='scheduled',
                    user=None  # 시스템 자동 동기화
                )
                
                result['success'] = sync_result.success
                result['sync_id'] = sync_result.sync_id
                result['pages_processed'] = sync_result.total_pages
                
                if not sync_result.success and sync_result.error:
                    result['error'] = sync_result.error
                
                logger.info(f"데이터베이스 '{database.title}' 동기화 완료 - "
                           f"페이지: {sync_result.total_pages}, 성공: {sync_result.success}")
                
            finally:
                # 락 해제
                cache.delete(lock_key)
        
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"데이터베이스 '{database.title}' 동기화 실패: {str(e)}")
            # 락 해제
            cache.delete(lock_key)
        
        return result
    
    def force_sync_database(self, database_id: int) -> bool:
        """특정 데이터베이스 강제 동기화 예약"""
        try:
            database = NotionDatabase.objects.get(id=database_id, is_active=True)
            force_sync_key = f"notion_force_sync_{database_id}"
            cache.set(force_sync_key, True, 60)  # 1분 내 실행
            
            logger.info(f"데이터베이스 '{database.title}' 강제 동기화 예약됨")
            return True
            
        except NotionDatabase.DoesNotExist:
            logger.error(f"데이터베이스 ID {database_id}를 찾을 수 없습니다")
            return False
    
    def get_sync_status_summary(self) -> Dict[str, Any]:
        """동기화 상태 요약 정보"""
        now = timezone.now()
        
        # 지난 24시간 동기화 통계
        recent_syncs = SyncHistory.objects.filter(
            started_at__gte=now - timedelta(days=1)
        )
        
        # 활성 데이터베이스별 마지막 동기화 상태
        active_databases = NotionDatabase.objects.filter(is_active=True)
        
        summary = {
            'total_active_databases': active_databases.count(),
            'recent_sync_stats': {
                'total': recent_syncs.count(),
                'completed': recent_syncs.filter(status='completed').count(),
                'failed': recent_syncs.filter(status='failed').count(),
                'in_progress': recent_syncs.filter(status__in=['started', 'in_progress']).count()
            },
            'databases_status': []
        }
        
        for db in active_databases:
            last_sync = db.sync_history.order_by('-started_at').first()
            
            db_status = {
                'database_id': db.id,
                'title': db.title,
                'last_synced': db.last_synced.isoformat() if db.last_synced else None,
                'sync_interval': db.sync_interval,
                'is_sync_overdue': False,
                'last_sync_status': None
            }
            
            if db.last_synced:
                time_since_sync = now - db.last_synced
                sync_interval = timedelta(seconds=db.sync_interval)
                db_status['is_sync_overdue'] = time_since_sync > sync_interval * 1.5
            
            if last_sync:
                db_status['last_sync_status'] = {
                    'status': last_sync.status,
                    'started_at': last_sync.started_at.isoformat(),
                    'success_rate': last_sync.success_rate,
                    'total_pages': last_sync.total_pages
                }
            
            summary['databases_status'].append(db_status)
        
        return summary


class NotionChangeDetector:
    """Notion 변경사항 감지"""
    
    def __init__(self):
        self.sync_service = NotionSyncService()
    
    def detect_database_changes(self, database: NotionDatabase) -> Dict[str, Any]:
        """데이터베이스 변경사항 감지"""
        changes = {
            'database_id': database.id,
            'has_changes': False,
            'schema_changed': False,
            'pages_changed': 0,
            'new_pages': 0,
            'updated_pages': 0,
            'deleted_pages': 0
        }
        
        try:
            # 스키마 변경 확인
            current_schema = self.sync_service.notion_client.get_database(database.notion_id)
            if self._has_schema_changed(database, current_schema):
                changes['schema_changed'] = True
                changes['has_changes'] = True
            
            # 페이지 변경사항 확인 (최근 동기화 이후)
            if database.last_synced:
                page_changes = self._detect_page_changes(database)
                changes.update(page_changes)
                if page_changes['pages_changed'] > 0:
                    changes['has_changes'] = True
            
        except Exception as e:
            logger.error(f"데이터베이스 {database.title} 변경사항 감지 실패: {str(e)}")
        
        return changes
    
    def _has_schema_changed(self, database: NotionDatabase, current_schema: Dict) -> bool:
        """스키마 변경 확인"""
        if not database.schema:
            return True
        
        stored_properties = database.schema.get('properties', {})
        current_properties = current_schema.get('properties', {})
        
        # 속성 개수 변경
        if len(stored_properties) != len(current_properties):
            return True
        
        # 속성 타입이나 설정 변경
        for prop_name, stored_config in stored_properties.items():
            current_config = current_properties.get(prop_name)
            if not current_config:
                return True  # 속성 삭제됨
            
            if stored_config.get('type') != current_config.get('type'):
                return True  # 속성 타입 변경
        
        return False
    
    def _detect_page_changes(self, database: NotionDatabase) -> Dict[str, int]:
        """페이지 변경사항 감지"""
        changes = {
            'pages_changed': 0,
            'new_pages': 0,
            'updated_pages': 0,
            'deleted_pages': 0
        }
        
        try:
            # Notion에서 최근 수정된 페이지들 조회
            since = database.last_synced
            filter_criteria = {
                'filter': {
                    'property': 'last_edited_time',
                    'date': {
                        'after': since.isoformat()
                    }
                }
            }
            
            recent_pages = self.sync_service.notion_client.query_database_pages(
                database.notion_id, 
                filter_criteria
            )
            
            if recent_pages:
                for page_data in recent_pages:
                    page_id = page_data['id']
                    
                    # 로컬에 존재하는지 확인
                    existing_page = database.pages.filter(notion_id=page_id).first()
                    
                    if not existing_page:
                        changes['new_pages'] += 1
                    else:
                        # 수정 시간 비교
                        notion_edited = datetime.fromisoformat(
                            page_data['last_edited_time'].replace('Z', '+00:00')
                        )
                        if notion_edited > existing_page.notion_last_edited_time:
                            changes['updated_pages'] += 1
                
                changes['pages_changed'] = changes['new_pages'] + changes['updated_pages']
        
        except Exception as e:
            logger.error(f"페이지 변경사항 감지 실패: {str(e)}")
        
        return changes


# 스케줄러 인스턴스
notion_scheduler = NotionSyncScheduler()
change_detector = NotionChangeDetector()


def run_notion_sync_job():
    """Notion 동기화 작업 실행 (외부 스케줄러용)"""
    return notion_scheduler.run_scheduled_sync()


def detect_notion_changes():
    """Notion 변경사항 감지 작업"""
    active_databases = NotionDatabase.objects.filter(is_active=True)
    changes_detected = []
    
    for database in active_databases:
        changes = change_detector.detect_database_changes(database)
        if changes['has_changes']:
            changes_detected.append(changes)
            
            # 변경사항이 있으면 동기화 예약
            notion_scheduler.force_sync_database(database.id)
    
    return {
        'total_databases_checked': active_databases.count(),
        'databases_with_changes': len(changes_detected),
        'changes_details': changes_detected
    }