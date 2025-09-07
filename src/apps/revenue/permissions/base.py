"""기본 권한 클래스 및 유틸리티"""
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
