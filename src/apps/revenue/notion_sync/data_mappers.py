"""데이터 변환 및 매핑"""
import logging
from decimal import Decimal
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class DataMapper:
    """데이터 변환 매퍼"""
    
    def fetch_django_data(self) -> List:
        """Django 데이터베이스에서 데이터 가져오기"""
        from apps.revenue.models import RevenueRecord
        return list(RevenueRecord.objects.all())
    
    async def sync_to_django(self, notion_item) -> str:
        """Notion 데이터를 Django로 동기화"""
        from apps.revenue.models import RevenueRecord
        
        try:
            # Notion 데이터 파싱
            parsed_data = self._parse_notion_item(notion_item)
            
            # Django 레코드 찾기 또는 생성
            record, created = RevenueRecord.objects.update_or_create(
                notion_page_id=notion_item['id'],
                defaults=parsed_data
            )
            
            return 'created' if created else 'updated'
            
        except Exception as e:
            logger.error(f"Django 동기화 실패: {e}")
            return 'error'
    
    def _parse_notion_item(self, notion_item) -> Dict:
        """Notion 아이템 파싱"""
        properties = notion_item.get('properties', {})
        
        return {
            'date': self._parse_date(properties.get('날짜')),
            'amount': self._parse_number(properties.get('금액')),
            'client_name': self._parse_text(properties.get('클라이언트')),
            'project_name': self._parse_text(properties.get('프로젝트')),
            'status': self._parse_select(properties.get('상태')),
        }
    
    def _parse_date(self, prop):
        """날짜 속성 파싱"""
        if prop and prop['type'] == 'date' and prop['date']:
            return datetime.fromisoformat(prop['date']['start'])
        return None
    
    def _parse_number(self, prop):
        """숫자 속성 파싱"""
        if prop and prop['type'] == 'number':
            return Decimal(str(prop['number']))
        return Decimal('0')
    
    def _parse_text(self, prop):
        """텍스트 속성 파싱"""
        if prop and prop['type'] == 'title':
            return ''.join([t['plain_text'] for t in prop['title']])
        return ''
    
    def _parse_select(self, prop):
        """선택 속성 파싱"""
        if prop and prop['type'] == 'select' and prop['select']:
            return prop['select']['name']
        return ''
