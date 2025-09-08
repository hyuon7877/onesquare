"""
Group creation and management
그룹 생성 및 관리
"""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.auth_system.models import UserType, UserGroup, CustomUser
from apps.auth_system.permissions import (
    PERMISSION_MATRIX, PermissionLevel, GROUP_DESCRIPTIONS
)


class GroupManager:
    """그룹 관리자"""
    
    def __init__(self, command, permission_manager):
        self.command = command
        self.permission_manager = permission_manager
        self.created_groups = 0
        self.created_user_groups = 0
    
    def create_user_groups(self):
        """사용자 그룹 생성"""
        self.command.stdout.write('👥 사용자 그룹 생성 중...')
        
        for user_type in UserType:
            self._create_group_for_user_type(user_type)
        
        self.command.log_summary(
            '사용자 그룹',
            len(UserType),
            self.created_groups
        )
    
    def _create_group_for_user_type(self, user_type):
        """특정 사용자 타입에 대한 그룹 생성"""
        group_name = f'OneSquare_{user_type.value}'
        
        # Django Group 생성
        group, group_created = Group.objects.get_or_create(
            name=group_name,
            defaults={'name': group_name}
        )
        
        if group_created:
            self.created_groups += 1
            self.command.log_action('➕', f'그룹 생성: {group_name}')
        
        # UserGroup 확장 정보 생성
        self._create_user_group_extension(group, user_type)
    
    def _create_user_group_extension(self, group, user_type):
        """UserGroup 확장 정보 생성"""
        user_group, created = UserGroup.objects.get_or_create(
            group=group,
            defaults={
                'user_type': user_type.value,
                'description': GROUP_DESCRIPTIONS.get(user_type.value, '')
            }
        )
        
        if created:
            self.created_user_groups += 1
            self.command.log_action('➕', f'확장 그룹 정보 생성: {user_type.label}')
        elif self.command.force and not self.command.dry_run:
            user_group.description = GROUP_DESCRIPTIONS.get(user_type.value, '')
            user_group.save()
            self.command.log_action('🔄', f'확장 그룹 정보 업데이트: {user_type.label}')
    
    def assign_group_permissions(self):
        """그룹별 권한 할당"""
        self.command.stdout.write('🔐 그룹별 권한 할당 중...')
        
        user_content_type = ContentType.objects.get_for_model(CustomUser)
        
        for user_type in UserType:
            self._assign_permissions_to_user_type(user_type, user_content_type)
    
    def _assign_permissions_to_user_type(self, user_type, content_type):
        """특정 사용자 타입에 권한 할당"""
        group_name = f'OneSquare_{user_type.value}'
        
        try:
            group = Group.objects.get(name=group_name)
        except Group.DoesNotExist:
            self.command.stdout.write(
                self.command.style.ERROR(f'  ❌ 그룹을 찾을 수 없음: {group_name}')
            )
            return
        
        # 기존 권한 초기화 (force 모드인 경우)
        if self.command.force and not self.command.dry_run:
            group.permissions.clear()
        
        # 권한 할당
        assigned_count = self._assign_permissions(group, user_type, content_type)
        
        if not self.command.dry_run:
            self.command.stdout.write(
                f'  ✅ {user_type.label} 그룹에 {assigned_count}개 권한 할당'
            )
    
    def _assign_permissions(self, group, user_type, content_type):
        """그룹에 권한 할당"""
        user_permissions = PERMISSION_MATRIX.get(user_type.value, {})
        assigned_count = 0
        
        for module, level in user_permissions.items():
            if level == PermissionLevel.NONE:
                continue
            
            permission_codes = self.permission_manager.get_permission_codes_for_level(
                module, level
            )
            
            for perm_code in permission_codes:
                if self._add_permission_to_group(group, perm_code, content_type):
                    assigned_count += 1
        
        return assigned_count
    
    def _add_permission_to_group(self, group, perm_code, content_type):
        """그룹에 단일 권한 추가"""
        try:
            permission = Permission.objects.get(
                codename=perm_code,
                content_type=content_type
            )
            
            if not self.command.dry_run:
                group.permissions.add(permission)
            
            return True
            
        except Permission.DoesNotExist:
            self.command.stdout.write(
                self.command.style.WARNING(f'  ⚠️  권한을 찾을 수 없음: {perm_code}')
            )
            return False