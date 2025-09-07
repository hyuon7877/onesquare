#!/usr/bin/env python3
"""
고복잡도 모듈 분할 자동화 스크립트
복잡한 단일 모듈을 여러 작은 모듈로 분할
"""

import os
import sys
import ast
import shutil
from pathlib import Path
from datetime import datetime
import argparse

class ModuleSplitter:
    def __init__(self, module_path, output_dir, parts=4):
        self.module_path = Path(module_path)
        self.output_dir = Path(output_dir)
        self.parts = parts
        self.module_name = self.module_path.stem
        
    def analyze_module(self):
        """모듈 구조 분석"""
        with open(self.module_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        # 클래스와 함수 수집
        classes = []
        functions = []
        constants = []
        imports = []
        
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                classes.append({
                    'name': node.name,
                    'lineno': node.lineno,
                    'end_lineno': node.end_lineno,
                    'methods': len([n for n in node.body if isinstance(n, ast.FunctionDef)])
                })
            elif isinstance(node, ast.FunctionDef):
                functions.append({
                    'name': node.name,
                    'lineno': node.lineno,
                    'end_lineno': node.end_lineno,
                    'complexity': self._calculate_complexity(node)
                })
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(ast.unparse(node))
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        constants.append(target.id)
        
        return {
            'classes': classes,
            'functions': functions,
            'constants': constants,
            'imports': imports,
            'total_lines': len(content.split('\n'))
        }
    
    def _calculate_complexity(self, node):
        """함수 복잡도 계산"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity
    
    def split_permissions(self):
        """Permissions 모듈 특화 분할"""
        print(f"📁 Permissions 모듈 분할 중...")
        
        # 백업
        backup_path = self.module_path.parent / f"{self.module_name}_backup.py"
        if not backup_path.exists():
            shutil.copy(self.module_path, backup_path)
        
        # 출력 디렉토리 생성
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. base.py - 기본 권한 클래스와 상수
        self._create_base_module()
        
        # 2. user.py - 사용자 권한 관리
        self._create_user_module()
        
        # 3. group.py - 그룹 권한 관리
        self._create_group_module()
        
        # 4. decorators.py - 권한 데코레이터
        self._create_decorators_module()
        
        # 5. __init__.py - 통합 import
        self._create_init_module()
        
        print(f"✅ Permissions 모듈이 {self.output_dir}에 분할되었습니다")
    
    def _create_base_module(self):
        """base.py 생성"""
        content = '''"""
기본 권한 정의 및 상수
"""

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.db import models
from enum import Enum
from utils.logger import get_logger

logger = get_logger(__name__)

# 시스템 권한 정의
SYSTEM_PERMISSIONS = {
    # 대시보드 권한
    'view_dashboard': '대시보드 조회',
    'add_dashboard': '대시보드 추가',
    'change_dashboard': '대시보드 수정',
    'delete_dashboard': '대시보드 삭제',
    
    # 사용자 관리 권한
    'view_user_management': '사용자 관리 조회',
    'add_user_management': '사용자 추가',
    'change_user_management': '사용자 수정',
    'delete_user_management': '사용자 삭제',
    
    # 리포트 권한
    'view_reports': '리포트 조회',
    'add_reports': '리포트 생성',
    'change_reports': '리포트 수정',
    'delete_reports': '리포트 삭제',
    
    # 캘린더 권한
    'view_calendar': '캘린더 조회',
    'add_calendar': '캘린더 일정 추가',
    'change_calendar': '캘린더 일정 수정',
    'delete_calendar': '캘린더 일정 삭제',
    
    # 현장 리포트 권한
    'view_field_reports': '현장 리포트 조회',
    'add_field_reports': '현장 리포트 작성',
    'change_field_reports': '현장 리포트 수정',
    'delete_field_reports': '현장 리포트 삭제',
}

# 그룹별 설명
GROUP_DESCRIPTIONS = {
    'super_admin': '최고관리자 - 모든 시스템 기능에 대한 전체 권한',
    'manager': '중간관리자 - 팀 관리 및 대부분 기능 권한',
    'team_member': '팀원 - 기본 업무 기능 권한',
    'partner': '파트너 - 협력업체용 제한된 권한',
    'contractor': '도급사 - 도급업체용 제한된 권한',
    'custom': '커스텀 - 개별 맞춤 권한 설정'
}

class PermissionLevel(models.TextChoices):
    """권한 레벨 정의"""
    FULL = 'full', '전체 권한'
    READ_WRITE = 'read_write', '읽기/쓰기'
    READ_ONLY = 'read_only', '읽기 전용'
    NONE = 'none', '권한 없음'

class SystemModule(models.TextChoices):
    """시스템 모듈 정의"""
    DASHBOARD = 'dashboard', '대시보드'
    USER_MANAGEMENT = 'user_management', '사용자 관리'
    REPORTS = 'reports', '리포트'
    CALENDAR = 'calendar', '캘린더'
    FIELD_REPORTS = 'field_reports', '현장 리포트'
    NOTION_API = 'notion_api', 'Notion API'
    SETTINGS = 'settings', '설정'
    ADMIN = 'admin', '관리자'
'''
        
        with open(self.output_dir / 'base.py', 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _create_user_module(self):
        """user.py 생성"""
        content = '''"""
사용자 권한 관리
"""

from django.contrib.auth.models import User, Permission
from .base import SYSTEM_PERMISSIONS, logger
from utils.logger import log_user_action

def get_user_permissions(user):
    """사용자의 모든 권한 조회"""
    if not user or not user.is_authenticated:
        return set()
    
    if user.is_superuser:
        return set(SYSTEM_PERMISSIONS.keys())
    
    # 사용자 직접 권한 + 그룹 권한
    user_perms = set()
    for perm in user.user_permissions.all():
        user_perms.add(f"{perm.content_type.app_label}.{perm.codename}")
    
    for group in user.groups.all():
        for perm in group.permissions.all():
            user_perms.add(f"{perm.content_type.app_label}.{perm.codename}")
    
    return user_perms

def has_permission(user, permission_code):
    """사용자가 특정 권한을 가지고 있는지 확인"""
    if not user or not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    user_perms = get_user_permissions(user)
    return permission_code in user_perms

def grant_permission(user, permission_code):
    """사용자에게 권한 부여"""
    try:
        perm = Permission.objects.get(codename=permission_code)
        user.user_permissions.add(perm)
        log_user_action(user, 'grant_permission', {'permission': permission_code})
        logger.info(f"권한 부여: {user.username} - {permission_code}")
        return True
    except Permission.DoesNotExist:
        logger.error(f"권한을 찾을 수 없음: {permission_code}")
        return False

def revoke_permission(user, permission_code):
    """사용자 권한 회수"""
    try:
        perm = Permission.objects.get(codename=permission_code)
        user.user_permissions.remove(perm)
        log_user_action(user, 'revoke_permission', {'permission': permission_code})
        logger.info(f"권한 회수: {user.username} - {permission_code}")
        return True
    except Permission.DoesNotExist:
        logger.error(f"권한을 찾을 수 없음: {permission_code}")
        return False
'''
        
        with open(self.output_dir / 'user.py', 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _create_group_module(self):
        """group.py 생성"""
        content = '''"""
그룹 권한 관리
"""

from django.contrib.auth.models import Group, Permission
from .base import GROUP_DESCRIPTIONS, SYSTEM_PERMISSIONS, logger

# 그룹별 권한 매트릭스
GROUP_PERMISSION_MATRIX = {
    'super_admin': list(SYSTEM_PERMISSIONS.keys()),  # 모든 권한
    
    'manager': [
        'view_dashboard', 'add_dashboard', 'change_dashboard',
        'view_reports', 'add_reports', 'change_reports',
        'view_calendar', 'add_calendar', 'change_calendar',
        'view_field_reports', 'add_field_reports', 'change_field_reports',
        'view_settings', 'change_settings',
    ],
    
    'team_member': [
        'view_dashboard',
        'view_reports', 'add_reports',
        'view_calendar', 'add_calendar', 'change_calendar',
        'view_field_reports', 'add_field_reports', 'change_field_reports',
    ],
    
    'partner': [
        'view_dashboard',
        'view_reports',
        'view_calendar',
        'view_field_reports', 'add_field_reports',
    ],
    
    'contractor': [
        'view_dashboard',
        'view_field_reports', 'add_field_reports',
    ],
    
    'custom': []  # 개별 설정
}

def create_default_groups():
    """기본 그룹 생성"""
    created_groups = []
    
    for group_name, description in GROUP_DESCRIPTIONS.items():
        group, created = Group.objects.get_or_create(name=group_name)
        
        if created:
            logger.info(f"그룹 생성: {group_name}")
            created_groups.append(group_name)
            
            # 권한 할당
            permissions = GROUP_PERMISSION_MATRIX.get(group_name, [])
            for perm_code in permissions:
                try:
                    perm = Permission.objects.get(codename=perm_code)
                    group.permissions.add(perm)
                except Permission.DoesNotExist:
                    logger.warning(f"권한을 찾을 수 없음: {perm_code}")
    
    return created_groups

def get_group_permissions(group_name):
    """그룹의 권한 목록 조회"""
    try:
        group = Group.objects.get(name=group_name)
        return [p.codename for p in group.permissions.all()]
    except Group.DoesNotExist:
        logger.error(f"그룹을 찾을 수 없음: {group_name}")
        return []

def add_user_to_group(user, group_name):
    """사용자를 그룹에 추가"""
    try:
        group = Group.objects.get(name=group_name)
        user.groups.add(group)
        logger.info(f"사용자 그룹 추가: {user.username} -> {group_name}")
        return True
    except Group.DoesNotExist:
        logger.error(f"그룹을 찾을 수 없음: {group_name}")
        return False
'''
        
        with open(self.output_dir / 'group.py', 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _create_decorators_module(self):
        """decorators.py 생성"""
        content = '''"""
권한 확인 데코레이터
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from .user import has_permission
from .base import logger

def require_permission(permission_code):
    """권한 확인 데코레이터"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "로그인이 필요합니다.")
                return redirect('login')
            
            if not has_permission(request.user, permission_code):
                logger.warning(f"권한 거부: {request.user.username} - {permission_code}")
                raise PermissionDenied(f"'{permission_code}' 권한이 필요합니다.")
            
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator

def require_any_permission(*permission_codes):
    """여러 권한 중 하나라도 있으면 허용"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "로그인이 필요합니다.")
                return redirect('login')
            
            for permission_code in permission_codes:
                if has_permission(request.user, permission_code):
                    return view_func(request, *args, **kwargs)
            
            logger.warning(f"권한 거부: {request.user.username} - {permission_codes}")
            raise PermissionDenied(f"다음 권한 중 하나가 필요합니다: {', '.join(permission_codes)}")
        return wrapped_view
    return decorator

def require_all_permissions(*permission_codes):
    """모든 권한을 가져야 허용"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "로그인이 필요합니다.")
                return redirect('login')
            
            for permission_code in permission_codes:
                if not has_permission(request.user, permission_code):
                    logger.warning(f"권한 거부: {request.user.username} - {permission_code}")
                    raise PermissionDenied(f"모든 권한이 필요합니다: {', '.join(permission_codes)}")
            
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator
'''
        
        with open(self.output_dir / 'decorators.py', 'w', encoding='utf-8') as f:
            f.write(content)
    
    def split_validators(self):
        """Validators 모듈 특화 분할"""
        print(f"📁 Validators 모듈 분할 중...")
        
        # 백업
        backup_path = self.module_path.parent / f"{self.module_name}_backup.py"
        if not backup_path.exists():
            shutil.copy(self.module_path, backup_path)
            print(f"✅ 백업 생성: {backup_path.name}")
        
        # 출력 디렉토리 생성
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. password.py - 패스워드 검증
        self._create_password_validators()
        
        # 2. input.py - 입력 데이터 검증
        self._create_input_validators()
        
        # 3. patterns.py - 보안 패턴 정의
        self._create_patterns_module()
        
        # 4. utils.py - 검증 유틸리티
        self._create_validator_utils()
        
        # 5. __init__.py - 통합
        self._create_validators_init()
        
        print(f"✅ Validators 모듈이 {self.output_dir}에 분할되었습니다!")
        return self.output_dir
    
    def _create_password_validators(self):
        """password.py - 패스워드 검증 클래스"""
        with open(self.module_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        content = '''"""패스워드 복잡성 검증"""
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
        
        if self.require_numbers and not re.search(r'\\d', password):
            errors.append(_('비밀번호에 숫자가 포함되어야 합니다.'))
        
        if self.require_special and not re.search(r'[!@#$%^&*()_+\\-=\\[\\]{};\\':"\\\\|,.<>\\?]', password):
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
'''
        
        with open(self.output_dir / 'password.py', 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _create_input_validators(self):
        """input.py - 입력 데이터 검증"""
        content = '''"""입력 데이터 sanitization 및 검증"""
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
            r'\\.\\./',  # 디렉토리 탐색
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
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False
        
        # 위험한 패턴 검증
        if not cls.validate_xss(email) or not cls.validate_sql_injection(email):
            return False
        
        return True
'''
        
        with open(self.output_dir / 'input.py', 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _create_patterns_module(self):
        """patterns.py - 보안 패턴 정의"""
        content = '''"""보안 검증을 위한 패턴 정의"""

# XSS 위험 패턴
XSS_PATTERNS = [
    r'<script[^>]*>.*?</script>',
    r'javascript:',
    r'on\\w+\\s*=',
    r'<iframe[^>]*>',
    r'<object[^>]*>',
    r'<embed[^>]*>',
    r'<link[^>]*>',
    r'<meta[^>]*>',
    r'<style[^>]*>.*?</style>',
    r'vbscript:',
    r'data:text/html',
    r'expression\\s*\\(',
    r'@import',
]

# SQL Injection 위험 패턴
SQL_INJECTION_PATTERNS = [
    r'(union|select|insert|update|delete|drop|create|alter|exec|execute)\\s+',
    r';\\s*(union|select|insert|update|delete|drop|create|alter|exec|execute)\\s+',
    r'--\\s*$',
    r'/\\*.*?\\*/',
    r"'\\s*(or|and)\\s+",
    r'"\\s*(or|and)\\s+',
    r'(or|and)\\s+\\d+\\s*=\\s*\\d+',
    r'(or|and)\\s+\\w+\\s*(=|like)\\s*',
    r'having\\s+\\d+=\\d+',
    r'group\\s+by\\s+',
    r'order\\s+by\\s+',
]

# 위험한 파일 확장자
DANGEROUS_EXTENSIONS = [
    'exe', 'bat', 'cmd', 'com', 'pif', 'scr', 'vbs', 'js', 'jar',
    'php', 'asp', 'aspx', 'jsp', 'pl', 'py', 'rb', 'sh', 'ps1'
]

# 일반적인 패스워드 패턴
COMMON_PASSWORD_PATTERNS = [
    r'^password.*',
    r'^123.*',
    r'^qwerty.*',
    r'^admin.*',
    r'^letmein.*',
    r'^welcome.*',
    r'^.*123$',
    r'^.*password$',
]

# 위험한 URL 스키마
DANGEROUS_URL_SCHEMES = [
    'javascript:',
    'data:',
    'vbscript:',
    'file:',
    'about:',
    'chrome:',
]

# 파일명 위험 패턴
DANGEROUS_FILENAME_PATTERNS = [
    r'\\.\\./',  # 디렉토리 탐색
    r'^(con|prn|aux|nul|com[1-9]|lpt[1-9])$',  # Windows 예약어
    r'[<>:"|?*]',  # 특수문자
    r'^\\.',  # 숨김 파일
    r'\\$',  # 특수 경로
]
'''
        
        with open(self.output_dir / 'patterns.py', 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _create_validator_utils(self):
        """utils.py - 검증 유틸리티"""
        content = '''"""검증 관련 유틸리티 함수"""
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
    value = re.sub(r'\\s+', ' ', value)
    
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
        r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})',
        r'\\1****@\\2',
        value_str
    )
    
    # 전화번호
    value_str = re.sub(
        r'(01[0-9])-?([0-9]{3,4})-?([0-9]{4})',
        r'\\1-****-\\3',
        value_str
    )
    
    # 주민등록번호 패턴
    value_str = re.sub(
        r'\\b[0-9]{6}-?[0-9]{7}\\b',
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
'''
        
        with open(self.output_dir / 'utils.py', 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _create_validators_init(self):
        """__init__.py - Validators 모듈 통합"""
        content = '''"""OneSquare 보안 검증 시스템
분할된 검증 모듈 통합
"""

from .password import ComplexPasswordValidator
from .input import InputSanitizationValidator
from .patterns import (
    XSS_PATTERNS,
    SQL_INJECTION_PATTERNS,
    DANGEROUS_EXTENSIONS,
    COMMON_PASSWORD_PATTERNS,
    DANGEROUS_URL_SCHEMES,
    DANGEROUS_FILENAME_PATTERNS,
)
from .utils import (
    is_safe_string,
    normalize_whitespace,
    validate_korean_phone,
    validate_korean_business_number,
    sanitize_for_log,
    get_validation_errors,
)

__all__ = [
    # Password
    'ComplexPasswordValidator',
    
    # Input
    'InputSanitizationValidator',
    
    # Patterns
    'XSS_PATTERNS',
    'SQL_INJECTION_PATTERNS',
    'DANGEROUS_EXTENSIONS',
    'COMMON_PASSWORD_PATTERNS',
    'DANGEROUS_URL_SCHEMES',
    'DANGEROUS_FILENAME_PATTERNS',
    
    # Utils
    'is_safe_string',
    'normalize_whitespace',
    'validate_korean_phone',
    'validate_korean_business_number',
    'sanitize_for_log',
    'get_validation_errors',
]

# 버전 정보
__version__ = '1.0.0'
__author__ = 'OneSquare Team'
'''
        
        with open(self.output_dir / '__init__.py', 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _create_init_module(self):
        """__init__.py 생성"""
        content = '''"""
OneSquare 권한 관리 시스템
분할된 권한 모듈 통합
"""

from .base import (
    SYSTEM_PERMISSIONS,
    GROUP_DESCRIPTIONS,
    PermissionLevel,
    SystemModule,
)

from .user import (
    get_user_permissions,
    has_permission,
    grant_permission,
    revoke_permission,
)

from .group import (
    GROUP_PERMISSION_MATRIX,
    create_default_groups,
    get_group_permissions,
    add_user_to_group,
)

from .decorators import (
    require_permission,
    require_any_permission,
    require_all_permissions,
)

__all__ = [
    # Base
    'SYSTEM_PERMISSIONS',
    'GROUP_DESCRIPTIONS',
    'PermissionLevel',
    'SystemModule',
    
    # User
    'get_user_permissions',
    'has_permission',
    'grant_permission',
    'revoke_permission',
    
    # Group
    'GROUP_PERMISSION_MATRIX',
    'create_default_groups',
    'get_group_permissions',
    'add_user_to_group',
    
    # Decorators
    'require_permission',
    'require_any_permission',
    'require_all_permissions',
]
'''
        
        with open(self.output_dir / '__init__.py', 'w', encoding='utf-8') as f:
            f.write(content)

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='모듈 분할 도구')
    parser.add_argument('--module', required=True, help='분할할 모듈 (permissions/validators)')
    parser.add_argument('--parts', type=int, default=4, help='분할 개수')
    
    args = parser.parse_args()
    
    if args.module == 'permissions':
        module_path = 'src/apps/auth_system/permissions.py'
        output_dir = 'src/apps/auth_system/permissions'
        
        splitter = ModuleSplitter(module_path, output_dir, args.parts)
        splitter.split_permissions()
        
    elif args.module == 'validators':
        module_path = 'src/apps/security/validators.py'
        output_dir = 'src/apps/security/validators'
        
        splitter = ModuleSplitter(module_path, output_dir, args.parts)
        splitter.split_validators()
        
    else:
        print(f"알 수 없는 모듈: {args.module}")
        sys.exit(1)

if __name__ == "__main__":
    main()