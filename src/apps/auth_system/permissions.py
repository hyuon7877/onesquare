"""
OneSquare 사용자 권한 관리 시스템

이 모듈은 OneSquare 시스템의 6개 사용자 그룹별 권한 매트릭스와
Django Permission 시스템을 활용한 세밀한 권한 제어를 제공합니다.

사용자 그룹:
1. 최고관리자 (SUPER_ADMIN) - 모든 권한
2. 중간관리자 (MANAGER) - 관리 권한 (사용자 관리 제외)
3. 팀원 (TEAM_MEMBER) - 기본 업무 권한
4. 파트너 (PARTNER) - 파트너 관련 권한
5. 도급사 (CONTRACTOR) - 도급 관련 권한  
6. 커스텀 (CUSTOM) - 개별 설정 권한
"""

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from enum import Enum
import logging

# 시스템 권한 정의 (Django Permission 생성용)
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
    
    # Notion API 권한
    'view_notion_api': 'Notion API 조회',
    'add_notion_api': 'Notion API 생성',
    'change_notion_api': 'Notion API 수정',
    'delete_notion_api': 'Notion API 삭제',
    
    # 설정 권한
    'view_settings': '설정 조회',
    'add_settings': '설정 추가',
    'change_settings': '설정 수정',
    'delete_settings': '설정 삭제',
    
    # 관리자 권한
    'view_admin': '관리자 페이지 조회',
    'add_admin': '관리자 기능 추가',
    'change_admin': '관리자 기능 수정',
    'delete_admin': '관리자 기능 삭제',
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

logger = logging.getLogger(__name__)

from django.db import models


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
    SETTINGS = 'settings', '시스템 설정'
    ADMIN = 'admin', '시스템 관리'


# 사용자 그룹별 권한 매트릭스
PERMISSION_MATRIX = {
    'SUPER_ADMIN': {
        SystemModule.DASHBOARD: PermissionLevel.FULL,
        SystemModule.USER_MANAGEMENT: PermissionLevel.FULL,
        SystemModule.REPORTS: PermissionLevel.FULL,
        SystemModule.CALENDAR: PermissionLevel.FULL,
        SystemModule.FIELD_REPORTS: PermissionLevel.FULL,
        SystemModule.NOTION_API: PermissionLevel.FULL,
        SystemModule.SETTINGS: PermissionLevel.FULL,
        SystemModule.ADMIN: PermissionLevel.FULL,
    },
    'MANAGER': {
        SystemModule.DASHBOARD: PermissionLevel.FULL,
        SystemModule.USER_MANAGEMENT: PermissionLevel.READ_WRITE,  # 승인 권한만
        SystemModule.REPORTS: PermissionLevel.FULL,
        SystemModule.CALENDAR: PermissionLevel.FULL,
        SystemModule.FIELD_REPORTS: PermissionLevel.FULL,
        SystemModule.NOTION_API: PermissionLevel.READ_WRITE,
        SystemModule.SETTINGS: PermissionLevel.READ_ONLY,
        SystemModule.ADMIN: PermissionLevel.NONE,
    },
    'TEAM_MEMBER': {
        SystemModule.DASHBOARD: PermissionLevel.READ_ONLY,
        SystemModule.USER_MANAGEMENT: PermissionLevel.NONE,
        SystemModule.REPORTS: PermissionLevel.READ_ONLY,
        SystemModule.CALENDAR: PermissionLevel.READ_WRITE,
        SystemModule.FIELD_REPORTS: PermissionLevel.NONE,
        SystemModule.NOTION_API: PermissionLevel.READ_ONLY,
        SystemModule.SETTINGS: PermissionLevel.NONE,
        SystemModule.ADMIN: PermissionLevel.NONE,
    },
    'PARTNER': {
        SystemModule.DASHBOARD: PermissionLevel.NONE,
        SystemModule.USER_MANAGEMENT: PermissionLevel.NONE,
        SystemModule.REPORTS: PermissionLevel.READ_ONLY,  # 자신 관련만
        SystemModule.CALENDAR: PermissionLevel.READ_ONLY,  # 자신 관련만
        SystemModule.FIELD_REPORTS: PermissionLevel.READ_WRITE,  # 현장 업무
        SystemModule.NOTION_API: PermissionLevel.READ_ONLY,
        SystemModule.SETTINGS: PermissionLevel.NONE,
        SystemModule.ADMIN: PermissionLevel.NONE,
    },
    'CONTRACTOR': {
        SystemModule.DASHBOARD: PermissionLevel.NONE,
        SystemModule.USER_MANAGEMENT: PermissionLevel.NONE,
        SystemModule.REPORTS: PermissionLevel.READ_ONLY,  # 자신 관련만
        SystemModule.CALENDAR: PermissionLevel.READ_ONLY,  # 자신 관련만
        SystemModule.FIELD_REPORTS: PermissionLevel.READ_WRITE,  # 현장 업무
        SystemModule.NOTION_API: PermissionLevel.READ_ONLY,
        SystemModule.SETTINGS: PermissionLevel.NONE,
        SystemModule.ADMIN: PermissionLevel.NONE,
    },
    'CUSTOM': {
        # 커스텀 그룹은 개별적으로 권한 설정
        SystemModule.DASHBOARD: PermissionLevel.NONE,
        SystemModule.USER_MANAGEMENT: PermissionLevel.NONE,
        SystemModule.REPORTS: PermissionLevel.NONE,
        SystemModule.CALENDAR: PermissionLevel.NONE,
        SystemModule.FIELD_REPORTS: PermissionLevel.NONE,
        SystemModule.NOTION_API: PermissionLevel.NONE,
        SystemModule.SETTINGS: PermissionLevel.NONE,
        SystemModule.ADMIN: PermissionLevel.NONE,
    }
}


# 세부 권한 정의
DETAILED_PERMISSIONS = {
    # 대시보드 권한
    'dashboard.view': '대시보드 조회',
    'dashboard.export': '대시보드 데이터 내보내기',
    'dashboard.customize': '대시보드 커스터마이징',
    
    # 사용자 관리 권한
    'user.view': '사용자 정보 조회',
    'user.add': '사용자 추가',
    'user.change': '사용자 정보 수정',
    'user.delete': '사용자 삭제',
    'user.approve': '사용자 승인',
    'user.manage_groups': '사용자 그룹 관리',
    
    # 리포트 권한
    'report.view_all': '모든 리포트 조회',
    'report.view_own': '본인 리포트만 조회',
    'report.create': '리포트 작성',
    'report.edit': '리포트 편집',
    'report.delete': '리포트 삭제',
    'report.export': '리포트 내보내기',
    'report.print': '리포트 인쇄',
    
    # 캘린더 권한
    'calendar.view_all': '전체 캘린더 조회',
    'calendar.view_own': '본인 캘린더만 조회',
    'calendar.create': '일정 생성',
    'calendar.edit': '일정 편집',
    'calendar.delete': '일정 삭제',
    'calendar.manage': '캘린더 관리',
    
    # 현장 리포트 권한
    'field_report.view': '현장 리포트 조회',
    'field_report.create': '현장 리포트 작성',
    'field_report.edit': '현장 리포트 편집',
    'field_report.delete': '현장 리포트 삭제',
    'field_report.approve': '현장 리포트 승인',
    
    # Notion API 권한
    'notion.read': 'Notion 데이터 읽기',
    'notion.write': 'Notion 데이터 쓰기',
    'notion.sync': 'Notion 데이터 동기화',
    'notion.manage': 'Notion 설정 관리',
    
    # 시스템 설정 권한
    'settings.view': '시스템 설정 조회',
    'settings.change': '시스템 설정 변경',
    'settings.backup': '시스템 백업',
    'settings.restore': '시스템 복원',
    
    # 관리자 권한
    'admin.full_access': '관리자 모든 권한',
    'admin.user_impersonate': '사용자 대리 로그인',
    'admin.system_logs': '시스템 로그 조회',
    'admin.maintenance': '시스템 유지보수',
}


# 사용자 타입별 세부 권한 매핑
USER_TYPE_PERMISSIONS = {
    'SUPER_ADMIN': [
        # 모든 권한
        'dashboard.view', 'dashboard.export', 'dashboard.customize',
        'user.view', 'user.add', 'user.change', 'user.delete', 'user.approve', 'user.manage_groups',
        'report.view_all', 'report.create', 'report.edit', 'report.delete', 'report.export', 'report.print',
        'calendar.view_all', 'calendar.create', 'calendar.edit', 'calendar.delete', 'calendar.manage',
        'field_report.view', 'field_report.create', 'field_report.edit', 'field_report.delete', 'field_report.approve',
        'notion.read', 'notion.write', 'notion.sync', 'notion.manage',
        'settings.view', 'settings.change', 'settings.backup', 'settings.restore',
        'admin.full_access', 'admin.user_impersonate', 'admin.system_logs', 'admin.maintenance',
    ],
    'MANAGER': [
        # 관리 권한 (사용자 생성/삭제 제외)
        'dashboard.view', 'dashboard.export', 'dashboard.customize',
        'user.view', 'user.change', 'user.approve',
        'report.view_all', 'report.create', 'report.edit', 'report.delete', 'report.export', 'report.print',
        'calendar.view_all', 'calendar.create', 'calendar.edit', 'calendar.delete', 'calendar.manage',
        'field_report.view', 'field_report.create', 'field_report.edit', 'field_report.approve',
        'notion.read', 'notion.write', 'notion.sync',
        'settings.view',
    ],
    'TEAM_MEMBER': [
        # 기본 업무 권한
        'dashboard.view',
        'report.view_own', 'report.create',
        'calendar.view_own', 'calendar.create', 'calendar.edit',
        'notion.read',
    ],
    'PARTNER': [
        # 파트너 권한
        'report.view_own',
        'calendar.view_own',
        'field_report.view', 'field_report.create', 'field_report.edit',
        'notion.read',
    ],
    'CONTRACTOR': [
        # 도급사 권한
        'report.view_own',
        'calendar.view_own',
        'field_report.view', 'field_report.create', 'field_report.edit',
        'notion.read',
    ],
    'CUSTOM': [
        # 커스텀 그룹은 개별 설정
    ]
}


class PermissionManager:
    """권한 관리 클래스"""
    
    @staticmethod
    def get_user_permissions(user):
        """사용자의 모든 권한 조회"""
        if not user or not user.is_authenticated:
            return []
        
        # 사용자 타입별 기본 권한
        base_permissions = USER_TYPE_PERMISSIONS.get(user.user_type.name, [])
        
        # Django 권한 시스템에서 추가 권한
        django_permissions = []
        if hasattr(user, 'user_permissions'):
            django_permissions = [
                perm.codename for perm in user.user_permissions.all()
            ]
        
        # 그룹 권한
        group_permissions = []
        if hasattr(user, 'groups'):
            for group in user.groups.all():
                group_permissions.extend([
                    perm.codename for perm in group.permissions.all()
                ])
        
        # 모든 권한 합치기
        all_permissions = set(base_permissions + django_permissions + group_permissions)
        return list(all_permissions)
    
    @staticmethod
    def has_permission(user, permission_code):
        """사용자가 특정 권한을 가지고 있는지 확인"""
        if not user or not user.is_authenticated:
            return False
        
        # 슈퍼유저는 모든 권한
        if user.is_superuser:
            return True
        
        user_permissions = PermissionManager.get_user_permissions(user)
        return permission_code in user_permissions
    
    @staticmethod
    def has_module_permission(user, module, level=PermissionLevel.READ_ONLY):
        """사용자가 특정 모듈에 대한 권한을 가지고 있는지 확인"""
        if not user or not user.is_authenticated:
            return False
        
        # 슈퍼유저는 모든 권한
        if user.is_superuser:
            return True
        
        user_type_permissions = PERMISSION_MATRIX.get(user.user_type.name, {})
        user_level = user_type_permissions.get(module, PermissionLevel.NONE)
        
        # 권한 레벨 비교
        level_hierarchy = {
            PermissionLevel.NONE: 0,
            PermissionLevel.READ_ONLY: 1,
            PermissionLevel.READ_WRITE: 2,
            PermissionLevel.FULL: 3,
        }
        
        required_level = level_hierarchy.get(level, 0)
        user_level_value = level_hierarchy.get(user_level, 0)
        
        return user_level_value >= required_level
    
    @staticmethod
    def filter_queryset_by_permission(user, queryset, permission_code):
        """권한에 따라 쿼리셋 필터링"""
        if not user or not user.is_authenticated:
            return queryset.none()
        
        # 슈퍼유저는 모든 데이터
        if user.is_superuser:
            return queryset
        
        # 전체 조회 권한 확인
        if PermissionManager.has_permission(user, permission_code + '_all'):
            return queryset
        
        # 본인 데이터만 조회 권한 확인
        if PermissionManager.has_permission(user, permission_code + '_own'):
            # 본인과 관련된 데이터만 필터링 (구체적인 로직은 모델에 따라 다름)
            if hasattr(queryset.model, 'user'):
                return queryset.filter(user=user)
            elif hasattr(queryset.model, 'created_by'):
                return queryset.filter(created_by=user)
        
        return queryset.none()
    
    @staticmethod
    def create_permissions():
        """시스템에 필요한 권한들을 생성"""
        from django.contrib.contenttypes.models import ContentType
        
        # OneSquare 앱의 ContentType 가져오기
        try:
            content_type = ContentType.objects.get_for_model(
                ContentType,  # 임시로 ContentType 사용
                for_concrete_model=False
            )
        except ContentType.DoesNotExist:
            logger.error("ContentType을 찾을 수 없습니다.")
            return
        
        created_permissions = []
        
        for perm_code, perm_name in DETAILED_PERMISSIONS.items():
            permission, created = Permission.objects.get_or_create(
                codename=perm_code,
                name=perm_name,
                content_type=content_type
            )
            if created:
                created_permissions.append(perm_code)
        
        if created_permissions:
            logger.info(f"생성된 권한: {created_permissions}")
        
        return created_permissions
    
    @staticmethod
    def assign_permissions_to_groups():
        """사용자 그룹에 권한 할당"""
        from django.contrib.auth.models import Group
        
        for user_type, permissions in USER_TYPE_PERMISSIONS.items():
            group_name = user_type.replace('_', ' ').title()
            
            try:
                group, created = Group.objects.get_or_create(name=group_name)
                
                # 그룹 권한 초기화
                group.permissions.clear()
                
                # 권한 할당
                for perm_code in permissions:
                    try:
                        permission = Permission.objects.get(codename=perm_code)
                        group.permissions.add(permission)
                    except Permission.DoesNotExist:
                        logger.warning(f"권한을 찾을 수 없음: {perm_code}")
                
                if created:
                    logger.info(f"그룹 생성: {group_name}")
                else:
                    logger.info(f"그룹 권한 업데이트: {group_name}")
                    
            except Exception as e:
                logger.error(f"그룹 권한 할당 오류: {user_type} - {e}")


class PermissionMixin:
    """권한 체크를 위한 믹스인"""
    
    required_permissions = []  # 필요한 권한 목록
    required_module = None     # 필요한 모듈
    required_level = PermissionLevel.READ_ONLY  # 필요한 권한 레벨
    
    def has_required_permissions(self, user):
        """필요한 권한을 가지고 있는지 확인"""
        if not user or not user.is_authenticated:
            return False
        
        # 개별 권한 확인
        for permission in self.required_permissions:
            if not PermissionManager.has_permission(user, permission):
                return False
        
        # 모듈 권한 확인
        if self.required_module:
            if not PermissionManager.has_module_permission(
                user, self.required_module, self.required_level
            ):
                return False
        
        return True
    
    def dispatch(self, request, *args, **kwargs):
        """권한 확인 후 뷰 실행"""
        if not self.has_required_permissions(request.user):
            from django.http import HttpResponseForbidden, JsonResponse
            
            if request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
                return JsonResponse({
                    'error': '접근 권한이 없습니다.',
                    'required_permissions': self.required_permissions,
                    'required_module': self.required_module,
                    'required_level': self.required_level
                }, status=403)
            else:
                return HttpResponseForbidden('접근 권한이 없습니다.')
        
        return super().dispatch(request, *args, **kwargs)