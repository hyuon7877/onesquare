"""분석 관련 권한"""
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
