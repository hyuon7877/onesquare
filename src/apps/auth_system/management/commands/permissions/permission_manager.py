"""
Permission creation and management
권한 생성 및 관리
"""

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.auth_system.models import CustomUser
from apps.auth_system.permissions import SYSTEM_PERMISSIONS


class PermissionManager:
    """권한 관리자"""
    
    def __init__(self, command):
        self.command = command
        self.created_count = 0
        self.updated_count = 0
    
    def create_system_permissions(self):
        """시스템 권한 생성"""
        self.command.stdout.write('📋 시스템 권한 생성 중...')
        
        # CustomUser ContentType 가져오기
        user_content_type = ContentType.objects.get_for_model(CustomUser)
        
        for perm_code, perm_name in SYSTEM_PERMISSIONS.items():
            self._create_or_update_permission(
                perm_code, 
                perm_name, 
                user_content_type
            )
        
        self.command.log_summary(
            '시스템 권한',
            len(SYSTEM_PERMISSIONS),
            self.created_count,
            self.updated_count
        )
    
    def _create_or_update_permission(self, code, name, content_type):
        """권한 생성 또는 업데이트"""
        permission, created = Permission.objects.get_or_create(
            codename=code,
            content_type=content_type,
            defaults={'name': name}
        )
        
        if created:
            self.created_count += 1
            self.command.log_action('➕', f'권한 생성: {code} - {name}')
        elif self.command.force:
            permission.name = name
            if not self.command.dry_run:
                permission.save()
            self.updated_count += 1
            self.command.log_action('🔄', f'권한 업데이트: {code} - {name}')
    
    def get_permission_codes_for_level(self, module, level):
        """권한 레벨에 따른 권한 코드 목록 반환"""
        from apps.auth_system.permissions import SystemModule, PermissionLevel
        
        base_codes = {
            SystemModule.DASHBOARD: 'dashboard',
            SystemModule.USER_MANAGEMENT: 'user_management', 
            SystemModule.REPORTS: 'reports',
            SystemModule.CALENDAR: 'calendar',
            SystemModule.FIELD_REPORTS: 'field_reports',
            SystemModule.NOTION_API: 'notion_api',
            SystemModule.SETTINGS: 'settings',
            SystemModule.ADMIN: 'admin'
        }
        
        base_code = base_codes.get(module, module.value.lower())
        
        if level == PermissionLevel.FULL:
            return [
                f'view_{base_code}',
                f'add_{base_code}', 
                f'change_{base_code}',
                f'delete_{base_code}'
            ]
        elif level == PermissionLevel.READ_WRITE:
            return [
                f'view_{base_code}',
                f'add_{base_code}',
                f'change_{base_code}'
            ]
        elif level == PermissionLevel.READ_ONLY:
            return [f'view_{base_code}']
        
        return []