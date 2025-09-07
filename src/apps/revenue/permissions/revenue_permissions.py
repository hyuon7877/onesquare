"""수익 관련 권한"""
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
