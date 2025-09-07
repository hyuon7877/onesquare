"""동기화 작업 관리"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from django.utils import timezone
from django.core.cache import cache
from .base import NotionSyncBase
from .notion_api import NotionAPIHandler
from .data_mappers import DataMapper
from .conflict_resolver import ConflictResolver

logger = logging.getLogger(__name__)

class SyncOperations(NotionSyncBase):
    """동기화 작업 처리"""
    
    def __init__(self):
        super().__init__()
        self.api_handler = NotionAPIHandler(self.notion_client, self.database_id)
        self.data_mapper = DataMapper()
        self.conflict_resolver = ConflictResolver()
    
    async def sync_all_revenue_data(self, user=None) -> Dict:
        """전체 매출 데이터 동기화"""
        if not self.is_sync_available():
            return {'success': False, 'message': 'Notion API 설정이 필요합니다.'}
        
        try:
            cache.set(self.sync_status_cache_key, 'running', timeout=300)
            
            # 데이터 가져오기
            notion_data = await self.api_handler.fetch_all_data()
            django_data = self.data_mapper.fetch_django_data()
            
            # 동기화 수행
            sync_result = await self._perform_bidirectional_sync(notion_data, django_data)
            
            # 완료 처리
            cache.set(self.last_sync_cache_key, timezone.now().isoformat(), timeout=None)
            cache.set(self.sync_status_cache_key, 'completed', timeout=60)
            
            return {
                'success': True,
                'message': '동기화가 완료되었습니다.',
                'result': sync_result
            }
            
        except Exception as e:
            logger.error(f"동기화 실패: {e}")
            return {'success': False, 'message': str(e)}
    
    async def _perform_bidirectional_sync(self, notion_data, django_data):
        """양방향 데이터 동기화"""
        created = 0
        updated = 0
        conflicts = 0
        
        # Notion → Django
        for item in notion_data:
            result = await self.data_mapper.sync_to_django(item)
            if result == 'created': created += 1
            elif result == 'updated': updated += 1
            elif result == 'conflict': conflicts += 1
        
        # Django → Notion
        for item in django_data:
            result = await self.api_handler.sync_to_notion(item)
            if result == 'created': created += 1
            elif result == 'updated': updated += 1
        
        return {
            'created': created,
            'updated': updated,
            'conflicts': conflicts
        }
