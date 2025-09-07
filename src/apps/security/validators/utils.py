"""검증 관련 유틸리티 함수"""
import re
import logging
from typing import Any, List, Optional, Dict

logger = logging.getLogger(__name__)

def is_safe_string(value: str, max_length: int = 1000) -> bool:
    """문자열이 안전한지 검증"""
    if not value or not isinstance(value, str):
        return True
    
    if len(value) > max_length:
        logger.warning(f"문자열 길이 초과: {len(value)} > {max_length}")
        return False
    
    # 기본 안전성 검사
    from .patterns import XSS_PATTERNS, SQL_INJECTION_PATTERNS
    
    value_lower = value.lower()
    
    # XSS 패턴 검사
    for pattern in XSS_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE | re.DOTALL):
            logger.warning(f"XSS 패턴 감지: {pattern}")
            return False
    
    # SQL Injection 패턴 검사
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, value_lower, re.IGNORECASE):
            logger.warning(f"SQL Injection 패턴 감지: {pattern}")
            return False
    
    return True

def normalize_whitespace(value: str) -> str:
    """공백 문자 정규화"""
    if not value:
        return value
    
    # 연속 공백을 단일 공백으로
    value = re.sub(r'\s+', ' ', value)
    
    # 앞뒤 공백 제거
    return value.strip()

def validate_korean_phone(phone: str) -> bool:
    """한국 전화번호 형식 검증"""
    if not phone:
        return False
    
    # 숫자와 하이픈만 남기기
    phone_digits = re.sub(r'[^0-9-]', '', phone)
    
    # 한국 전화번호 패턴
    patterns = [
        r'^01[0-9]-?[0-9]{3,4}-?[0-9]{4}$',  # 휴대폰
        r'^02-?[0-9]{3,4}-?[0-9]{4}$',  # 서울
        r'^0[3-6][0-9]-?[0-9]{3,4}-?[0-9]{4}$',  # 지역번호
    ]
    
    for pattern in patterns:
        if re.match(pattern, phone_digits):
            return True
    
    return False

def validate_korean_business_number(number: str) -> bool:
    """한국 사업자등록번호 검증"""
    if not number:
        return False
    
    # 숫자만 추출
    number = re.sub(r'[^0-9]', '', number)
    
    if len(number) != 10:
        return False
    
    # 사업자등록번호 검증 알고리즘
    check_id = [1, 3, 7, 1, 3, 7, 1, 3, 5]
    total = 0
    
    for i in range(9):
        total += int(number[i]) * check_id[i]
    
    total += (int(number[8]) * 5) // 10
    
    # 검증
    return (10 - (total % 10)) % 10 == int(number[9])

def sanitize_for_log(value: Any) -> str:
    """로그 출력용 데이터 sanitization"""
    if value is None:
        return 'None'
    
    value_str = str(value)
    
    # 개인정보 마스킹
    # 이메일
    value_str = re.sub(
        r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        r'\1****@\2',
        value_str
    )
    
    # 전화번호
    value_str = re.sub(
        r'(01[0-9])-?([0-9]{3,4})-?([0-9]{4})',
        r'\1-****-\3',
        value_str
    )
    
    # 주민등록번호 패턴
    value_str = re.sub(
        r'\b[0-9]{6}-?[0-9]{7}\b',
        r'******-*******',
        value_str
    )
    
    return value_str[:500]  # 최대 500자로 제한

def get_validation_errors(data: Dict, rules: Dict) -> List[str]:
    """데이터 검증 및 오류 메시지 반환"""
    errors = []
    
    for field, field_rules in rules.items():
        value = data.get(field)
        
        # 필수 필드 검사
        if field_rules.get('required') and not value:
            errors.append(f"{field}은(는) 필수 입력 항목입니다.")
            continue
        
        if not value:
            continue
        
        # 타입 검사
        expected_type = field_rules.get('type')
        if expected_type and not isinstance(value, expected_type):
            errors.append(f"{field}의 타입이 올바르지 않습니다.")
            continue
        
        # 길이 검사
        if 'min_length' in field_rules and len(str(value)) < field_rules['min_length']:
            errors.append(f"{field}은(는) 최소 {field_rules['min_length']}자 이상이어야 합니다.")
        
        if 'max_length' in field_rules and len(str(value)) > field_rules['max_length']:
            errors.append(f"{field}은(는) 최대 {field_rules['max_length']}자까지 가능합니다.")
        
        # 패턴 검사
        if 'pattern' in field_rules:
            if not re.match(field_rules['pattern'], str(value)):
                errors.append(f"{field}의 형식이 올바르지 않습니다.")
    
    return errors
