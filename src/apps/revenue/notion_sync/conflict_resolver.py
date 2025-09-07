"""데이터 동기화 충돌 해결"""
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class ConflictResolver:
    """동기화 충돌 해결"""
    
    def resolve_conflict(self, django_data, notion_data) -> Dict:
        """충돌 해결 로직"""
        # 타임스탬프 비교
        django_updated = django_data.get('updated_at')
        notion_updated = notion_data.get('last_edited_time')
        
        if self._is_newer(django_updated, notion_updated):
            return {'winner': 'django', 'data': django_data}
        else:
            return {'winner': 'notion', 'data': notion_data}
    
    def _is_newer(self, time1, time2) -> bool:
        """시간 비교"""
        if not time1: return False
        if not time2: return True
        
        if isinstance(time1, str):
            time1 = datetime.fromisoformat(time1)
        if isinstance(time2, str):
            time2 = datetime.fromisoformat(time2)
            
        return time1 > time2
    
    def merge_changes(self, django_data, notion_data) -> Dict:
        """변경사항 병합"""
        merged = {}
        
        # 각 필드별로 최신 데이터 선택
        for field in ['amount', 'client_name', 'project_name', 'status']:
            django_value = django_data.get(field)
            notion_value = notion_data.get(field)
            
            # 변경된 필드만 업데이트
            if django_value != notion_value:
                # 더 최근 변경사항 선택
                merged[field] = self._select_newer_value(
                    django_value, notion_value,
                    django_data.get('field_updated_at', {}),
                    notion_data.get('field_updated_at', {})
                )
            else:
                merged[field] = django_value
        
        return merged
    
    def _select_newer_value(self, value1, value2, updates1, updates2):
        """더 최근 값 선택"""
        # 구현 필요
        return value1
