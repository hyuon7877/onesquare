"""
Security validators for enhanced password and input validation
"""
import re
import string
from django.contrib.auth.password_validation import BasePasswordValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class ComplexPasswordValidator(BasePasswordValidator):
    """
    고급 패스워드 복잡성 검증기
    """
    
    def __init__(self, min_length=12, require_uppercase=True, require_lowercase=True,
                 require_numbers=True, require_special=True, 
                 require_non_sequential=True, require_non_repetitive=True):
        self.min_length = min_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_numbers = require_numbers
        self.require_special = require_special
        self.require_non_sequential = require_non_sequential
        self.require_non_repetitive = require_non_repetitive
    
    def validate(self, password, user=None):
        """패스워드 복잡성 검증"""
        errors = []
        
        # 최소 길이 검증
        if len(password) < self.min_length:
            errors.append(_('비밀번호는 최소 %d자 이상이어야 합니다.') % self.min_length)
        
        # 대문자 포함 검증
        if self.require_uppercase and not re.search(r'[A-Z]', password):
            errors.append(_('비밀번호에 대문자가 포함되어야 합니다.'))
        
        # 소문자 포함 검증
        if self.require_lowercase and not re.search(r'[a-z]', password):
            errors.append(_('비밀번호에 소문자가 포함되어야 합니다.'))
        
        # 숫자 포함 검증
        if self.require_numbers and not re.search(r'\d', password):
            errors.append(_('비밀번호에 숫자가 포함되어야 합니다.'))
        
        # 특수문자 포함 검증
        if self.require_special and not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\?]', password):
            errors.append(_('비밀번호에 특수문자가 포함되어야 합니다.'))
        
        # 연속된 문자 검증 (예: abc, 123)
        if self.require_non_sequential:
            if self._has_sequential_chars(password):
                errors.append(_('비밀번호에 연속된 문자를 사용할 수 없습니다.'))
        
        # 반복 문자 검증 (예: aaa, 111)
        if self.require_non_repetitive:
            if self._has_repetitive_chars(password):
                errors.append(_('비밀번호에 3개 이상 연속 반복되는 문자를 사용할 수 없습니다.'))
        
        # 사용자 정보와 유사성 검증
        if user:
            if self._is_similar_to_user_info(password, user):
                errors.append(_('비밀번호가 사용자 정보와 너무 유사합니다.'))
        
        # 일반적인 패스워드 패턴 검증
        if self._is_common_password_pattern(password):
            errors.append(_('너무 일반적인 비밀번호 패턴입니다.'))
        
        if errors:
            raise ValidationError(errors)
    
    def _has_sequential_chars(self, password):
        """연속된 문자 확인"""
        password_lower = password.lower()
        
        # 알파벳 연속 확인 (3자리 이상)
        for i in range(len(password_lower) - 2):
            if (ord(password_lower[i]) == ord(password_lower[i+1]) - 1 and 
                ord(password_lower[i+1]) == ord(password_lower[i+2]) - 1):
                return True
        
        # 숫자 연속 확인 (3자리 이상)
        for i in range(len(password) - 2):
            if (password[i].isdigit() and password[i+1].isdigit() and password[i+2].isdigit()):
                if (int(password[i]) == int(password[i+1]) - 1 and 
                    int(password[i+1]) == int(password[i+2]) - 1):
                    return True
        
        return False
    
    def _has_repetitive_chars(self, password):
        """반복 문자 확인"""
        for i in range(len(password) - 2):
            if password[i] == password[i+1] == password[i+2]:
                return True
        return False
    
    def _is_similar_to_user_info(self, password, user):
        """사용자 정보와 유사성 확인"""
        password_lower = password.lower()
        
        # 사용자명 확인
        if hasattr(user, 'username') and user.username:
            if user.username.lower() in password_lower:
                return True
        
        # 이메일 확인
        if hasattr(user, 'email') and user.email:
            email_parts = user.email.lower().split('@')
            if any(part in password_lower for part in email_parts if len(part) > 2):
                return True
        
        # 이름 확인
        if hasattr(user, 'first_name') and user.first_name:
            if user.first_name.lower() in password_lower:
                return True
        
        if hasattr(user, 'last_name') and user.last_name:
            if user.last_name.lower() in password_lower:
                return True
        
        return False
    
    def _is_common_password_pattern(self, password):
        """일반적인 패스워드 패턴 확인"""
        common_patterns = [
            r'^password.*',
            r'^123.*',
            r'^qwerty.*',
            r'^admin.*',
            r'^letmein.*',
            r'^welcome.*',
            r'^.*123$',
            r'^.*password$',
        ]
        
        password_lower = password.lower()
        for pattern in common_patterns:
            if re.match(pattern, password_lower):
                return True
        
        return False
    
    def get_help_text(self):
        """도움말 텍스트"""
        help_text = [
            f'비밀번호는 최소 {self.min_length}자 이상이어야 합니다.'
        ]
        
        if self.require_uppercase:
            help_text.append('대문자를 포함해야 합니다.')
        
        if self.require_lowercase:
            help_text.append('소문자를 포함해야 합니다.')
        
        if self.require_numbers:
            help_text.append('숫자를 포함해야 합니다.')
        
        if self.require_special:
            help_text.append('특수문자를 포함해야 합니다.')
        
        if self.require_non_sequential:
            help_text.append('연속된 문자는 사용할 수 없습니다.')
        
        if self.require_non_repetitive:
            help_text.append('3개 이상 연속 반복되는 문자는 사용할 수 없습니다.')
        
        help_text.append('사용자 정보와 유사한 비밀번호는 사용할 수 없습니다.')
        help_text.append('일반적인 비밀번호 패턴은 사용할 수 없습니다.')
        
        return ' '.join(help_text)


class InputSanitizationValidator:
    """
    입력 데이터 sanitization 및 검증
    """
    
    # XSS 위험 패턴
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
        r'<link[^>]*>',
        r'<meta[^>]*>',
        r'<style[^>]*>.*?</style>',
        r'vbscript:',
        r'data:text/html',
        r'expression\s*\(',
        r'@import',
    ]
    
    # SQL Injection 위험 패턴
    SQL_INJECTION_PATTERNS = [
        r'(union|select|insert|update|delete|drop|create|alter|exec|execute)\s+',
        r';\s*(union|select|insert|update|delete|drop|create|alter|exec|execute)\s+',
        r'--\s*$',
        r'/\*.*?\*/',
        r"'\s*(or|and)\s+",
        r'"\s*(or|and)\s+',
        r'(or|and)\s+\d+\s*=\s*\d+',
        r'(or|and)\s+\w+\s*(=|like)\s*',
        r'having\s+\d+=\d+',
        r'group\s+by\s+',
        r'order\s+by\s+',
    ]
    
    # 위험한 파일 확장자
    DANGEROUS_EXTENSIONS = [
        'exe', 'bat', 'cmd', 'com', 'pif', 'scr', 'vbs', 'js', 'jar',
        'php', 'asp', 'aspx', 'jsp', 'pl', 'py', 'rb', 'sh', 'ps1'
    ]
    
    @classmethod
    def sanitize_string(cls, value):
        """문자열 sanitization"""
        if not isinstance(value, str):
            return value
        
        # HTML 태그 제거
        value = re.sub(r'<[^>]+>', '', value)
        
        # 스크립트 태그 제거
        for pattern in cls.XSS_PATTERNS:
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
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return False
        
        return True
    
    @classmethod
    def validate_xss(cls, value):
        """XSS 공격 패턴 검증"""
        if not isinstance(value, str):
            return True
        
        for pattern in cls.XSS_PATTERNS:
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
        if extension in cls.DANGEROUS_EXTENSIONS:
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