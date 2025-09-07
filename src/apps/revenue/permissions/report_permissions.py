"""보고서 관련 권한"""
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
