"""
Password strength checker utilities
비밀번호 강도 검사 유틸리티
"""

import re
from django.utils.translation import gettext as _


class PasswordStrengthChecker:
    """비밀번호 강도 검사기"""
    
    def check_composition(self, password, require_uppercase, require_lowercase,
                         require_numbers, require_special):
        """비밀번호 구성 요소 검사"""
        errors = []
        
        if require_uppercase and not re.search(r'[A-Z]', password):
            errors.append(_('비밀번호에 대문자가 포함되어야 합니다.'))
        
        if require_lowercase and not re.search(r'[a-z]', password):
            errors.append(_('비밀번호에 소문자가 포함되어야 합니다.'))
        
        if require_numbers and not re.search(r'\d', password):
            errors.append(_('비밀번호에 숫자가 포함되어야 합니다.'))
        
        if require_special and not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\?]', password):
            errors.append(_('비밀번호에 특수문자가 포함되어야 합니다.'))
        
        return errors
    
    def has_sequential_chars(self, password):
        """연속된 문자 확인"""
        password_lower = password.lower()
        
        # 알파벳 연속 확인
        for i in range(len(password_lower) - 2):
            if self._is_sequential_alpha(password_lower[i:i+3]):
                return True
        
        # 숫자 연속 확인
        for i in range(len(password) - 2):
            if self._is_sequential_digit(password[i:i+3]):
                return True
        
        return False
    
    def _is_sequential_alpha(self, chars):
        """알파벳 연속성 확인"""
        if not all(c.isalpha() for c in chars):
            return False
        return (ord(chars[0]) == ord(chars[1]) - 1 and 
                ord(chars[1]) == ord(chars[2]) - 1)
    
    def _is_sequential_digit(self, chars):
        """숫자 연속성 확인"""
        if not all(c.isdigit() for c in chars):
            return False
        return (int(chars[0]) == int(chars[1]) - 1 and 
                int(chars[1]) == int(chars[2]) - 1)
    
    def has_repetitive_chars(self, password):
        """반복 문자 확인 (3개 이상)"""
        for i in range(len(password) - 2):
            if password[i] == password[i+1] == password[i+2]:
                return True
        return False
    
    def is_similar_to_user_info(self, password, user):
        """사용자 정보와 유사성 확인"""
        password_lower = password.lower()
        
        # 사용자명 확인
        if self._check_attribute_similarity(password_lower, user, 'username'):
            return True
        
        # 이메일 확인
        if hasattr(user, 'email') and user.email:
            email_parts = user.email.lower().split('@')
            if any(part in password_lower for part in email_parts if len(part) > 2):
                return True
        
        # 이름 확인
        if self._check_attribute_similarity(password_lower, user, 'first_name'):
            return True
        if self._check_attribute_similarity(password_lower, user, 'last_name'):
            return True
        
        return False
    
    def _check_attribute_similarity(self, password_lower, user, attribute):
        """속성 유사성 확인"""
        if hasattr(user, attribute):
            value = getattr(user, attribute)
            if value and value.lower() in password_lower:
                return True
        return False
    
    def is_common_pattern(self, password):
        """일반적인 패스워드 패턴 확인"""
        from .patterns import COMMON_PASSWORD_PATTERNS
        
        password_lower = password.lower()
        for pattern in COMMON_PASSWORD_PATTERNS:
            if re.match(pattern, password_lower):
                return True
        
        return False
    
    def get_strength_score(self, password):
        """비밀번호 강도 점수 계산 (0-100)"""
        score = 0
        
        # 길이 점수 (최대 30점)
        length_score = min(len(password) * 2, 30)
        score += length_score
        
        # 문자 다양성 점수 (최대 40점)
        if re.search(r'[a-z]', password):
            score += 10
        if re.search(r'[A-Z]', password):
            score += 10
        if re.search(r'\d', password):
            score += 10
        if re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\?]', password):
            score += 10
        
        # 패턴 회피 점수 (최대 30점)
        if not self.has_sequential_chars(password):
            score += 10
        if not self.has_repetitive_chars(password):
            score += 10
        if not self.is_common_pattern(password):
            score += 10
        
        return min(score, 100)