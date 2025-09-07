"""예산 관련 권한"""
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
