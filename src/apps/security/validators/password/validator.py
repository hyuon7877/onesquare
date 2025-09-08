"""
Password complexity validator
비밀번호 복잡성 검증기
"""

from django.contrib.auth.password_validation import BasePasswordValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from .checker import PasswordStrengthChecker


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
        self.checker = PasswordStrengthChecker()
    
    def validate(self, password, user=None):
        """패스워드 복잡성 검증"""
        errors = []
        
        # 길이 검증
        if len(password) < self.min_length:
            errors.append(_('비밀번호는 최소 %d자 이상이어야 합니다.') % self.min_length)
        
        # 문자 구성 검증
        composition_errors = self.checker.check_composition(
            password,
            self.require_uppercase,
            self.require_lowercase,
            self.require_numbers,
            self.require_special
        )
        errors.extend(composition_errors)
        
        # 패턴 검증
        if self.require_non_sequential and self.checker.has_sequential_chars(password):
            errors.append(_('비밀번호에 연속된 문자를 사용할 수 없습니다.'))
        
        if self.require_non_repetitive and self.checker.has_repetitive_chars(password):
            errors.append(_('비밀번호에 3개 이상 연속 반복되는 문자를 사용할 수 없습니다.'))
        
        # 사용자 정보 유사성 검증
        if user and self.checker.is_similar_to_user_info(password, user):
            errors.append(_('비밀번호가 사용자 정보와 너무 유사합니다.'))
        
        # 일반적인 패턴 검증
        if self.checker.is_common_pattern(password):
            errors.append(_('너무 일반적인 비밀번호 패턴입니다.'))
        
        if errors:
            raise ValidationError(errors)
    
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