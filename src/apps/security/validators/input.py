"""입력 데이터 sanitization 및 검증"""
import re
from .patterns import XSS_PATTERNS, SQL_INJECTION_PATTERNS, DANGEROUS_EXTENSIONS

class InputSanitizationValidator:
    """입력 데이터 sanitization 및 검증"""
    
    @classmethod
    def sanitize_string(cls, value):
        """문자열 sanitization"""
        if not isinstance(value, str):
            return value
        
        # HTML 태그 제거
        value = re.sub(r'<[^>]+>', '', value)
        
        # 스크립트 태그 제거
        for pattern in XSS_PATTERNS:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE | re.DOTALL)
        
        # 특수 문자 이스케이프
        value = value.replace('&', '&amp;')
        value = value.replace('<', '&lt;')
        value = value.replace('>', '&gt;')
        value = value.replace('"', '&quot;')
        value = value.replace("'", '&#x27;')
        value = value.replace('/', '&#x2F;')
        
        return value.strip()
    
    @classmethod
    def validate_sql_injection(cls, value):
        """SQL Injection 공격 패턴 검증"""
        if not isinstance(value, str):
            return True
        
        value_lower = value.lower()
        for pattern in SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return False
        
        return True
    
    @classmethod
    def validate_xss(cls, value):
        """XSS 공격 패턴 검증"""
        if not isinstance(value, str):
            return True
        
        for pattern in XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE | re.DOTALL):
                return False
        
        return True
    
    @classmethod
    def validate_file_upload(cls, filename):
        """파일 업로드 검증"""
        if not filename:
            return True
        
        # 파일 확장자 검증
        extension = filename.split('.')[-1].lower() if '.' in filename else ''
        if extension in DANGEROUS_EXTENSIONS:
            return False
        
        # 파일명 패턴 검증
        dangerous_patterns = [
            r'\.\./',  # 디렉토리 탐색
            r'^(con|prn|aux|nul|com[1-9]|lpt[1-9])$',  # Windows 예약어
            r'[<>:"|?*]',  # 특수문자
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, filename, re.IGNORECASE):
                return False
        
        return True
    
    @classmethod
    def validate_url(cls, url):
        """URL 검증"""
        if not url:
            return True
        
        # 위험한 URL 스키마 검증
        dangerous_schemes = ['javascript:', 'data:', 'vbscript:', 'file:']
        url_lower = url.lower()
        
        for scheme in dangerous_schemes:
            if url_lower.startswith(scheme):
                return False
        
        return True
    
    @classmethod
    def validate_email(cls, email):
        """이메일 주소 검증"""
        if not email:
            return True
        
        # 기본 이메일 패턴 검증
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False
        
        # 위험한 패턴 검증
        if not cls.validate_xss(email) or not cls.validate_sql_injection(email):
            return False
        
        return True
