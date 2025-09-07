"""Notion 동기화 기본 설정 및 초기화"""
import logging
from django.conf import settings
from django.core.cache import cache
from notion_client import Client

logger = logging.getLogger(__name__)

class NotionSyncBase:
    """Notion 동기화 기본 클래스"""
    
    def __init__(self):
        self.notion_client = None
        self.database_id = None
        self.sync_status_cache_key = 'revenue_notion_sync_status'
        self.last_sync_cache_key = 'revenue_notion_last_sync'
        self._initialize_notion_client()
    
    def _initialize_notion_client(self):
        """Notion 클라이언트 초기화"""
        try:
            notion_token = getattr(settings, 'NOTION_TOKEN', None)
            self.database_id = getattr(settings, 'NOTION_REVENUE_DATABASE_ID', None)
            
            if not notion_token or not self.database_id:
                logger.error("Notion API 설정이 누락되었습니다.")
                return False
            
            self.notion_client = Client(auth=notion_token)
            logger.info("Notion 클라이언트 초기화 완료")
            return True
            
        except Exception as e:
            logger.error(f"Notion 클라이언트 초기화 실패: {e}")
            return False
    
    def is_sync_available(self) -> bool:
        """동기화 서비스 사용 가능 여부 확인"""
        return self.notion_client is not None and self.database_id is not None
