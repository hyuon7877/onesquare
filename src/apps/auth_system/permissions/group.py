"""
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
