"""
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
