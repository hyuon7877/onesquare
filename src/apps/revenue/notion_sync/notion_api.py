"""Notion API 통신 처리"""
import logging
from typing import Dict, List, Optional
from notion_client.errors import APIResponseError

logger = logging.getLogger(__name__)

class NotionAPIHandler:
    """Notion API 통신 핸들러"""
    
    def __init__(self, notion_client, database_id):
        self.notion_client = notion_client
        self.database_id = database_id
    
    async def fetch_all_data(self) -> List[Dict]:
        """Notion에서 모든 데이터 가져오기"""
        try:
            response = self.notion_client.databases.query(
                database_id=self.database_id,
                sorts=[{"property": "날짜", "direction": "descending"}]
            )
            return response.get('results', [])
        except APIResponseError as e:
            logger.error(f"Notion API 오류: {e}")
            return []
    
    async def sync_to_notion(self, django_record) -> str:
        """Django 레코드를 Notion으로 동기화"""
        try:
            notion_page = self._find_notion_page(django_record)
            
            if notion_page:
                # 업데이트
                self.notion_client.pages.update(
                    page_id=notion_page['id'],
                    properties=self._prepare_notion_properties(django_record)
                )
                return 'updated'
            else:
                # 생성
                self.notion_client.pages.create(
                    parent={'database_id': self.database_id},
                    properties=self._prepare_notion_properties(django_record)
                )
                return 'created'
                
        except Exception as e:
            logger.error(f"Notion 동기화 실패: {e}")
            return 'error'
    
    def _find_notion_page(self, django_record):
        """Django 레코드와 매칭되는 Notion 페이지 찾기"""
        # 구현 필요
        return None
    
    def _prepare_notion_properties(self, django_record):
        """Django 레코드를 Notion 속성으로 변환"""
        # 구현 필요
        return {}
