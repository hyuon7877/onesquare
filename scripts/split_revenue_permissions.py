#!/usr/bin/env python3
"""Revenue Permissions 모듈 자동 분할"""

import shutil
from pathlib import Path

# 경로 설정
source_file = Path('src/apps/revenue/permissions.py')
target_dir = Path('src/apps/revenue/permissions')

# 백업
backup_file = source_file.parent / f"{source_file.stem}_backup.py"
if not backup_file.exists():
    shutil.copy(source_file, backup_file)
    print(f"✅ 백업 생성: {backup_file.name}")

# 대상 디렉토리 생성
target_dir.mkdir(exist_ok=True)

# 1. base.py - 기본 권한 클래스
with open(target_dir / 'base.py', 'w', encoding='utf-8') as f:
    f.write('''"""기본 권한 클래스 및 유틸리티"""
from rest_framework import permissions
from django.contrib.auth.models import User


class IsOwnerOrReadOnly(permissions.BasePermission):
    """소유자만 수정 가능, 나머지는 읽기 전용"""
    
    def has_object_permission(self, request, view, obj):
        # 읽기 권한은 모두에게 허용
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 쓰기 권한은 소유자에게만 허용
        return obj.owner == request.user


class IsManagerOrAbove(permissions.BasePermission):
    """매니저 이상 권한"""
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            (request.user.is_staff or 
             request.user.groups.filter(name__in=['Manager', 'Admin']).exists())
        )


class IsSupervisorOrAbove(permissions.BasePermission):
    """슈퍼바이저 이상 권한"""
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            (request.user.is_staff or 
             request.user.groups.filter(name__in=['Supervisor', 'Manager', 'Admin']).exists())
        )


class HasDepartmentAccess(permissions.BasePermission):
    """부서 접근 권한"""
    
    def has_object_permission(self, request, view, obj):
        # 같은 부서 사용자만 접근 가능
        if hasattr(obj, 'department'):
            return request.user.profile.department == obj.department
        return True
''')
    print("✅ base.py 생성")

# 2. revenue_permissions.py - 수익 관련 권한
with open(target_dir / 'revenue_permissions.py', 'w', encoding='utf-8') as f:
    f.write('''"""수익 관련 권한"""
from rest_framework import permissions
from .base import IsManagerOrAbove


class CanViewRevenue(permissions.BasePermission):
    """수익 조회 권한"""
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.has_perm('revenue.view_revenue')
        )


class CanEditRevenue(permissions.BasePermission):
    """수익 수정 권한"""
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.has_perm('revenue.change_revenue')
        )
    
    def has_object_permission(self, request, view, obj):
        # 작성자 또는 매니저만 수정 가능
        return (
            obj.created_by == request.user or
            request.user.groups.filter(name='Manager').exists()
        )


class CanDeleteRevenue(permissions.BasePermission):
    """수익 삭제 권한"""
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.has_perm('revenue.delete_revenue')
        )
    
    def has_object_permission(self, request, view, obj):
        # 매니저만 삭제 가능
        return request.user.groups.filter(name='Manager').exists()


class CanApproveRevenue(IsManagerOrAbove):
    """수익 승인 권한"""
    
    def has_object_permission(self, request, view, obj):
        # 매니저 이상만 승인 가능
        return super().has_permission(request, view) and obj.status == 'pending'
''')
    print("✅ revenue_permissions.py 생성")

# 3. report_permissions.py - 보고서 권한
with open(target_dir / 'report_permissions.py', 'w', encoding='utf-8') as f:
    f.write('''"""보고서 관련 권한"""
from rest_framework import permissions
from .base import IsSupervisorOrAbove


class CanViewReport(permissions.BasePermission):
    """보고서 조회 권한"""
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            (request.user.has_perm('revenue.view_report') or
             request.user.groups.filter(name__in=['Supervisor', 'Manager']).exists())
        )


class CanGenerateReport(IsSupervisorOrAbove):
    """보고서 생성 권한"""
    
    def has_permission(self, request, view):
        return (
            super().has_permission(request, view) and
            request.user.has_perm('revenue.add_report')
        )


class CanExportReport(permissions.BasePermission):
    """보고서 내보내기 권한"""
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.has_perm('revenue.export_report')
        )


class CanShareReport(permissions.BasePermission):
    """보고서 공유 권한"""
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.has_perm('revenue.share_report')
        )
    
    def has_object_permission(self, request, view, obj):
        # 작성자 또는 매니저만 공유 가능
        return (
            obj.created_by == request.user or
            request.user.is_staff
        )
''')
    print("✅ report_permissions.py 생성")

# 4. budget_permissions.py - 예산 권한
with open(target_dir / 'budget_permissions.py', 'w', encoding='utf-8') as f:
    f.write('''"""예산 관련 권한"""
from rest_framework import permissions
from .base import IsManagerOrAbove


class CanViewBudget(permissions.BasePermission):
    """예산 조회 권한"""
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.has_perm('revenue.view_budget')
        )
    
    def has_object_permission(self, request, view, obj):
        # 자신의 부서 예산만 조회 가능
        if hasattr(request.user, 'profile'):
            return obj.department == request.user.profile.department
        return False


class CanEditBudget(IsManagerOrAbove):
    """예산 수정 권한"""
    
    def has_permission(self, request, view):
        return (
            super().has_permission(request, view) and
            request.user.has_perm('revenue.change_budget')
        )


class CanApproveBudget(permissions.BasePermission):
    """예산 승인 권한"""
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.is_staff and
            request.user.has_perm('revenue.approve_budget')
        )


class CanAllocateBudget(IsManagerOrAbove):
    """예산 할당 권한"""
    
    def has_permission(self, request, view):
        return (
            super().has_permission(request, view) and
            request.user.has_perm('revenue.allocate_budget')
        )
''')
    print("✅ budget_permissions.py 생성")

# 5. analytics_permissions.py - 분석 권한
with open(target_dir / 'analytics_permissions.py', 'w', encoding='utf-8') as f:
    f.write('''"""분석 관련 권한"""
from rest_framework import permissions
from .base import IsSupervisorOrAbove


class CanViewAnalytics(permissions.BasePermission):
    """분석 데이터 조회 권한"""
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.has_perm('revenue.view_analytics')
        )


class CanAccessAdvancedAnalytics(IsSupervisorOrAbove):
    """고급 분석 접근 권한"""
    
    def has_permission(self, request, view):
        return (
            super().has_permission(request, view) and
            request.user.has_perm('revenue.advanced_analytics')
        )


class CanExportAnalytics(permissions.BasePermission):
    """분석 데이터 내보내기 권한"""
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.has_perm('revenue.export_analytics')
        )


class CanViewDashboard(permissions.BasePermission):
    """대시보드 조회 권한"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # 개인 또는 공개 대시보드만 조회 가능
        return (
            obj.is_public or
            obj.owner == request.user or
            request.user.is_staff
        )
''')
    print("✅ analytics_permissions.py 생성")

# 6. __init__.py
with open(target_dir / '__init__.py', 'w', encoding='utf-8') as f:
    f.write('''"""Revenue 권한 모듈

수익 관련 모든 권한 클래스 통합
"""

from .base import (
    IsOwnerOrReadOnly,
    IsManagerOrAbove,
    IsSupervisorOrAbove,
    HasDepartmentAccess
)

from .revenue_permissions import (
    CanViewRevenue,
    CanEditRevenue,
    CanDeleteRevenue,
    CanApproveRevenue
)

from .report_permissions import (
    CanViewReport,
    CanGenerateReport,
    CanExportReport,
    CanShareReport
)

from .budget_permissions import (
    CanViewBudget,
    CanEditBudget,
    CanApproveBudget,
    CanAllocateBudget
)

from .analytics_permissions import (
    CanViewAnalytics,
    CanAccessAdvancedAnalytics,
    CanExportAnalytics,
    CanViewDashboard
)

__all__ = [
    # Base permissions
    'IsOwnerOrReadOnly',
    'IsManagerOrAbove',
    'IsSupervisorOrAbove',
    'HasDepartmentAccess',
    
    # Revenue permissions
    'CanViewRevenue',
    'CanEditRevenue',
    'CanDeleteRevenue',
    'CanApproveRevenue',
    
    # Report permissions
    'CanViewReport',
    'CanGenerateReport',
    'CanExportReport',
    'CanShareReport',
    
    # Budget permissions
    'CanViewBudget',
    'CanEditBudget',
    'CanApproveBudget',
    'CanAllocateBudget',
    
    # Analytics permissions
    'CanViewAnalytics',
    'CanAccessAdvancedAnalytics',
    'CanExportAnalytics',
    'CanViewDashboard',
]
''')
    print("✅ __init__.py 생성")

# 원본 파일 제거
source_file.unlink()
print(f"🗑️ 원본 파일 제거: {source_file.name}")

print("\n✨ Revenue Permissions 모듈 분할 완료!")
print(f"📁 위치: {target_dir}")