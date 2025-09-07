"""
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
