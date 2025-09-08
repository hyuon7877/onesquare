"""패스워드 복잡성 검증"""
import re
from django.contrib.auth.password_validation import BasePasswordValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class ComplexPasswordValidator(BasePasswordValidator):
    """고급 패스워드 복잡성 검증기"""
    
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
        
        if len(password) < self.min_length:
            errors.append(_('비밀번호는 최소 %d자 이상이어야 합니다.') % self.min_length)
        
        if self.require_uppercase and not re.search(r'[A-Z]', password):
            errors.append(_('비밀번호에 대문자가 포함되어야 합니다.'))
        
        if self.require_lowercase and not re.search(r'[a-z]', password):
            errors.append(_('비밀번호에 소문자가 포함되어야 합니다.'))
        
        if self.require_numbers and not re.search(r'\d', password):
            errors.append(_('비밀번호에 숫자가 포함되어야 합니다.'))
        
        if self.require_special and not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\?]', password):
            errors.append(_('비밀번호에 특수문자가 포함되어야 합니다.'))
        
        if self.require_non_sequential and self._has_sequential_chars(password):
            errors.append(_('비밀번호에 연속된 문자를 사용할 수 없습니다.'))
        
        if self.require_non_repetitive and self._has_repetitive_chars(password):
            errors.append(_('비밀번호에 3개 이상 연속 반복되는 문자를 사용할 수 없습니다.'))
        
        if user and self._is_similar_to_user_info(password, user):
            errors.append(_('비밀번호가 사용자 정보와 너무 유사합니다.'))
        
        if self._is_common_password_pattern(password):
            errors.append(_('너무 일반적인 비밀번호 패턴입니다.'))
        
        if errors:
            raise ValidationError(errors)
    
    def _has_sequential_chars(self, password):
        """연속된 문자 확인"""
        password_lower = password.lower()
        
        for i in range(len(password_lower) - 2):
            if (ord(password_lower[i]) == ord(password_lower[i+1]) - 1 and 
                ord(password_lower[i+1]) == ord(password_lower[i+2]) - 1):
                return True
        
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
        
        if hasattr(user, 'username') and user.username:
            if user.username.lower() in password_lower:
                return True
        
        if hasattr(user, 'email') and user.email:
            email_parts = user.email.lower().split('@')
            if any(part in password_lower for part in email_parts if len(part) > 2):
                return True
        
        if hasattr(user, 'first_name') and user.first_name:
            if user.first_name.lower() in password_lower:
                return True
        
        if hasattr(user, 'last_name') and user.last_name:
            if user.last_name.lower() in password_lower:
                return True
        
        return False
    
    def _is_common_password_pattern(self, password):
        """일반적인 패스워드 패턴 확인"""
        from .patterns import COMMON_PASSWORD_PATTERNS
        
        password_lower = password.lower()
        for pattern in COMMON_PASSWORD_PATTERNS:
            if re.match(pattern, password_lower):
                return True
        
        return False
    
    def get_help_text(self):
        """도움말 텍스트"""
        help_text = [f'비밀번호는 최소 {self.min_length}자 이상이어야 합니다.']
        
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
