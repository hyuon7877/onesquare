"""
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
