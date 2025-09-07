"""
JSON 처리 공통 유틸리티
41개 모듈에서 사용되는 JSON 기능 통합
"""

import json
from decimal import Decimal
from datetime import date, datetime
from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)


class ExtendedJSONEncoder(DjangoJSONEncoder):
    """확장된 JSON 인코더 (Decimal, datetime 등 지원)"""
    
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)


def safe_json_loads(json_string, default=None):
    """안전한 JSON 파싱"""
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"JSON parsing error: {e}")
        return default if default is not None else {}


def safe_json_dumps(data, indent=None):
    """안전한 JSON 직렬화"""
    try:
        return json.dumps(data, cls=ExtendedJSONEncoder, ensure_ascii=False, indent=indent)
    except (TypeError, ValueError) as e:
        logger.error(f"JSON serialization error: {e}")
        return '{}'


def create_success_response(data=None, message="Success", status=200):
    """성공 응답 생성"""
    response_data = {
        'success': True,
        'message': message,
        'timestamp': datetime.now().isoformat()
    }
    if data is not None:
        response_data['data'] = data
    return JsonResponse(response_data, status=status, encoder=ExtendedJSONEncoder)


def create_error_response(error=None, message="Error occurred", status=400):
    """에러 응답 생성"""
    response_data = {
        'success': False,
        'message': message,
        'timestamp': datetime.now().isoformat()
    }
    if error:
        response_data['error'] = str(error)
    return JsonResponse(response_data, status=status, encoder=ExtendedJSONEncoder)


def parse_notion_json(notion_response):
    """Notion API 응답 파싱"""
    if not notion_response:
        return {}
    
    if isinstance(notion_response, str):
        return safe_json_loads(notion_response, {})
    
    return notion_response


def format_notion_properties(data):
    """Notion 프로퍼티 포맷팅"""
    properties = {}
    
    for key, value in data.items():
        if isinstance(value, str):
            properties[key] = {
                "title": [{"text": {"content": value}}]
            }
        elif isinstance(value, (int, float)):
            properties[key] = {
                "number": value
            }
        elif isinstance(value, bool):
            properties[key] = {
                "checkbox": value
            }
        elif isinstance(value, datetime):
            properties[key] = {
                "date": {"start": value.isoformat()}
            }
        elif isinstance(value, list):
            properties[key] = {
                "multi_select": [{"name": item} for item in value]
            }
        else:
            properties[key] = {
                "rich_text": [{"text": {"content": str(value)}}]
            }
    
    return properties


def extract_notion_content(notion_page):
    """Notion 페이지에서 컨텐츠 추출"""
    if not notion_page or 'properties' not in notion_page:
        return {}
    
    content = {}
    properties = notion_page.get('properties', {})
    
    for key, prop in properties.items():
        prop_type = prop.get('type')
        
        if prop_type == 'title':
            content[key] = prop.get('title', [{}])[0].get('text', {}).get('content', '')
        elif prop_type == 'rich_text':
            texts = prop.get('rich_text', [])
            content[key] = ' '.join(t.get('text', {}).get('content', '') for t in texts)
        elif prop_type == 'number':
            content[key] = prop.get('number')
        elif prop_type == 'checkbox':
            content[key] = prop.get('checkbox', False)
        elif prop_type == 'date':
            date_obj = prop.get('date', {})
            if date_obj:
                content[key] = date_obj.get('start')
        elif prop_type == 'select':
            select = prop.get('select', {})
            if select:
                content[key] = select.get('name', '')
        elif prop_type == 'multi_select':
            content[key] = [item.get('name', '') for item in prop.get('multi_select', [])]
        else:
            content[key] = prop
    
    return content


def validate_json_schema(data, schema):
    """JSON 스키마 검증"""
    required_fields = schema.get('required', [])
    properties = schema.get('properties', {})
    
    errors = []
    
    # 필수 필드 확인
    for field in required_fields:
        if field not in data:
            errors.append(f"Required field '{field}' is missing")
    
    # 타입 확인
    for field, value in data.items():
        if field in properties:
            expected_type = properties[field].get('type')
            if expected_type:
                if expected_type == 'string' and not isinstance(value, str):
                    errors.append(f"Field '{field}' should be string")
                elif expected_type == 'number' and not isinstance(value, (int, float)):
                    errors.append(f"Field '{field}' should be number")
                elif expected_type == 'boolean' and not isinstance(value, bool):
                    errors.append(f"Field '{field}' should be boolean")
                elif expected_type == 'array' and not isinstance(value, list):
                    errors.append(f"Field '{field}' should be array")
                elif expected_type == 'object' and not isinstance(value, dict):
                    errors.append(f"Field '{field}' should be object")
    
    return len(errors) == 0, errors


def merge_json_objects(*objects):
    """여러 JSON 객체 병합"""
    result = {}
    for obj in objects:
        if isinstance(obj, dict):
            result.update(obj)
    return result


def get_nested_value(data, path, default=None):
    """중첩된 JSON에서 값 추출 (점 표기법 지원)"""
    keys = path.split('.')
    value = data
    
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
            if value is None:
                return default
        else:
            return default
    
    return value


def set_nested_value(data, path, value):
    """중첩된 JSON에 값 설정"""
    keys = path.split('.')
    current = data
    
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value
    return data