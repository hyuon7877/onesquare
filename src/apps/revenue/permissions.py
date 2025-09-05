"""
OneSquare 매출 관리 시스템 - 권한 관리
6개 사용자 그룹별 매출 데이터 접근 권한 및 마스킹 시스템
"""

from django.contrib.auth.models import User, Group
from django.core.exceptions import PermissionDenied
from rest_framework import permissions
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class UserRole:
    """사용자 역할 정의"""
    SUPER_ADMIN = 'super_admin'          # 최고관리자
    ADMIN = 'admin'                      # 관리자  
    MIDDLE_MANAGER = 'middle_manager'    # 중간관리자
    TEAM_MEMBER = 'team_member'          # 팀원
    PARTNER = 'partner'                  # 파트너/도급사
    CLIENT = 'client'                    # 고객
    
    ALL_ROLES = [
        SUPER_ADMIN, ADMIN, MIDDLE_MANAGER, 
        TEAM_MEMBER, PARTNER, CLIENT
    ]
    
    ROLE_NAMES = {
        SUPER_ADMIN: '최고관리자',
        ADMIN: '관리자',
        MIDDLE_MANAGER: '중간관리자', 
        TEAM_MEMBER: '팀원',
        PARTNER: '파트너/도급사',
        CLIENT: '고객',
    }

class RevenuePermissionManager:
    """매출 권한 관리자"""
    
    @staticmethod
    def get_user_role(user):
        """사용자 역할 조회"""
        if not user or not user.is_authenticated:
            return None
            
        # 슈퍼유저는 최고관리자
        if user.is_superuser:
            return UserRole.SUPER_ADMIN
            
        # 그룹 기반 역할 확인
        user_groups = user.groups.values_list('name', flat=True)
        
        role_group_mapping = {
            'super_admin': UserRole.SUPER_ADMIN,
            'admin': UserRole.ADMIN,
            'middle_manager': UserRole.MIDDLE_MANAGER,
            'team_member': UserRole.TEAM_MEMBER,
            'partner': UserRole.PARTNER,
            'client': UserRole.CLIENT,
        }
        
        # 가장 높은 권한 반환 (순서가 중요)
        for group_name, role in role_group_mapping.items():
            if group_name in user_groups:
                return role
                
        # 기본값은 팀원
        return UserRole.TEAM_MEMBER
    
    @staticmethod
    def has_revenue_access(user, revenue_record=None):
        """매출 데이터 접근 권한 확인"""
        user_role = RevenuePermissionManager.get_user_role(user)
        
        if not user_role:
            return False
            
        # 최고관리자와 관리자는 모든 데이터 접근 가능
        if user_role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
            return True
            
        # 특정 매출 기록에 대한 접근 권한 확인
        if revenue_record:
            return RevenuePermissionManager._check_record_access(user, user_role, revenue_record)
            
        return True  # 기본 목록 조회는 허용 (필터링은 별도 처리)
    
    @staticmethod
    def _check_record_access(user, user_role, revenue_record):
        """개별 매출 기록 접근 권한 확인"""
        
        # 중간관리자: 본인이 매니저인 프로젝트 또는 팀원으로 참여한 프로젝트
        if user_role == UserRole.MIDDLE_MANAGER:
            if (revenue_record.project.project_manager == user or 
                user in revenue_record.project.team_members.all()):
                return True
                
        # 팀원: 본인이 영업담당자이거나 프로젝트 팀원인 경우
        elif user_role == UserRole.TEAM_MEMBER:
            if (revenue_record.sales_person == user or 
                user in revenue_record.project.team_members.all()):
                return True
                
        # 파트너: 본인이 참여한 프로젝트만
        elif user_role == UserRole.PARTNER:
            if user in revenue_record.project.team_members.all():
                return True
                
        # 고객: 본인 회사 프로젝트만
        elif user_role == UserRole.CLIENT:
            # 사용자 프로필에서 고객 정보 확인 필요
            user_client = getattr(user, 'client_profile', None)
            if user_client and revenue_record.client == user_client:
                return True
                
        return False
    
    @staticmethod 
    def filter_revenue_queryset(queryset, user):
        """사용자 권한에 따른 매출 쿼리셋 필터링"""
        user_role = RevenuePermissionManager.get_user_role(user)
        
        if not user_role:
            return queryset.none()
            
        # 최고관리자와 관리자는 모든 데이터 조회 가능
        if user_role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
            return queryset
            
        # 중간관리자: 관리하는 프로젝트의 매출만
        elif user_role == UserRole.MIDDLE_MANAGER:
            return queryset.filter(
                models.Q(project__project_manager=user) |
                models.Q(project__team_members=user)
            ).distinct()
            
        # 팀원: 본인 관련 매출만
        elif user_role == UserRole.TEAM_MEMBER:
            return queryset.filter(
                models.Q(sales_person=user) |
                models.Q(project__team_members=user)
            ).distinct()
            
        # 파트너: 참여 프로젝트 매출만
        elif user_role == UserRole.PARTNER:
            return queryset.filter(project__team_members=user).distinct()
            
        # 고객: 본인 회사 매출만
        elif user_role == UserRole.CLIENT:
            user_client = getattr(user, 'client_profile', None)
            if user_client:
                return queryset.filter(client=user_client)
            else:
                return queryset.none()
                
        return queryset.none()
    
    @staticmethod
    def mask_revenue_data(revenue_data, user):
        """권한에 따른 매출 데이터 마스킹"""
        user_role = RevenuePermissionManager.get_user_role(user)
        
        # 최고관리자와 관리자는 모든 데이터 표시
        if user_role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
            return revenue_data
            
        # 데이터 복사 (원본 보호)
        masked_data = revenue_data.copy() if isinstance(revenue_data, dict) else {}
        
        # 중간관리자: 부분 마스킹
        if user_role == UserRole.MIDDLE_MANAGER:
            masked_data = RevenuePermissionManager._apply_partial_masking(masked_data)
            
        # 팀원: 제한적 정보만 표시
        elif user_role == UserRole.TEAM_MEMBER:
            masked_data = RevenuePermissionManager._apply_team_member_masking(masked_data)
            
        # 파트너: 해당 프로젝트 관련 정보만
        elif user_role == UserRole.PARTNER:
            masked_data = RevenuePermissionManager._apply_partner_masking(masked_data)
            
        # 고객: 매우 제한적 정보
        elif user_role == UserRole.CLIENT:
            masked_data = RevenuePermissionManager._apply_client_masking(masked_data)
            
        return masked_data
    
    @staticmethod
    def _apply_partial_masking(data):
        """부분 마스킹 적용 (중간관리자용)"""
        if 'amount' in data:
            amount = data['amount']
            if isinstance(amount, (int, float, Decimal)):
                # 10의 자리 이하 마스킹 (예: 1,234,567 -> 1,234,5**)
                masked_amount = int(amount / 100) * 100
                data['amount'] = f"{masked_amount:,}**"
                data['is_masked'] = True
                
        # 세부 계약 조건 숨김
        sensitive_fields = ['tax_amount', 'invoice_number', 'notes']
        for field in sensitive_fields:
            if field in data:
                data[field] = "***"
                
        return data
    
    @staticmethod
    def _apply_team_member_masking(data):
        """팀원용 마스킹 적용"""
        if 'amount' in data:
            amount = data['amount']
            if isinstance(amount, (int, float, Decimal)):
                # 천의 자리 이하 마스킹 (예: 1,234,567 -> 1,234,***)
                masked_amount = int(amount / 1000) * 1000
                data['amount'] = f"{masked_amount:,}***"
                data['is_masked'] = True
                
        # 민감 정보 완전 숨김
        sensitive_fields = ['tax_amount', 'net_amount', 'invoice_number', 'notes', 'due_date']
        for field in sensitive_fields:
            if field in data:
                data[field] = "***"
                
        return data
    
    @staticmethod
    def _apply_partner_masking(data):
        """파트너용 마스킹 적용"""
        # 파트너는 전체 금액의 범위만 확인 가능
        if 'amount' in data:
            amount = data['amount']
            if isinstance(amount, (int, float, Decimal)):
                # 금액 범위로 표시
                amount_range = RevenuePermissionManager._get_amount_range(amount)
                data['amount'] = amount_range
                data['is_masked'] = True
                
        # 대부분의 세부 정보 숨김
        sensitive_fields = ['tax_amount', 'net_amount', 'invoice_number', 'notes', 'due_date', 'payment_date']
        for field in sensitive_fields:
            if field in data:
                data[field] = "***"
                
        return data
    
    @staticmethod
    def _apply_client_masking(data):
        """고객용 마스킹 적용"""
        # 고객은 프로젝트 진행상황 정도만 확인 가능
        if 'amount' in data:
            data['amount'] = "프로젝트 진행 중"
            data['is_masked'] = True
            
        # 거의 모든 세부 정보 숨김
        sensitive_fields = [
            'tax_amount', 'net_amount', 'invoice_number', 
            'notes', 'due_date', 'payment_date', 'invoice_date'
        ]
        for field in sensitive_fields:
            if field in data:
                data[field] = "***"
                
        return data
    
    @staticmethod
    def _get_amount_range(amount):
        """금액 범위 계산"""
        amount = float(amount)
        
        if amount < 1000000:  # 100만원 미만
            return "100만원 미만"
        elif amount < 5000000:  # 500만원 미만
            return "100만원~500만원"
        elif amount < 10000000:  # 1000만원 미만
            return "500만원~1000만원"
        elif amount < 50000000:  # 5000만원 미만
            return "1000만원~5000만원"
        elif amount < 100000000:  # 1억원 미만
            return "5000만원~1억원"
        else:
            return "1억원 이상"

class RevenuePermission(permissions.BasePermission):
    """매출 데이터 접근 권한 클래스"""
    
    def has_permission(self, request, view):
        """기본 권한 확인"""
        if not request.user or not request.user.is_authenticated:
            return False
            
        # 매출 데이터 접근 권한 확인
        return RevenuePermissionManager.has_revenue_access(request.user)
    
    def has_object_permission(self, request, view, obj):
        """객체별 권한 확인"""
        return RevenuePermissionManager.has_revenue_access(request.user, obj)

class RevenueReadOnlyPermission(permissions.BasePermission):
    """매출 데이터 읽기 전용 권한"""
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
            
        # 읽기 전용 요청만 허용
        if request.method not in permissions.SAFE_METHODS:
            user_role = RevenuePermissionManager.get_user_role(request.user)
            # 관리자급만 수정 가능
            return user_role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]
            
        return RevenuePermissionManager.has_revenue_access(request.user)
    
    def has_object_permission(self, request, view, obj):
        if request.method not in permissions.SAFE_METHODS:
            user_role = RevenuePermissionManager.get_user_role(request.user)
            return user_role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]
            
        return RevenuePermissionManager.has_revenue_access(request.user, obj)

def require_revenue_permission(permission_type='read'):
    """매출 권한 데코레이터"""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied("로그인이 필요합니다.")
                
            user_role = RevenuePermissionManager.get_user_role(request.user)
            
            # 쓰기 권한 확인
            if permission_type == 'write':
                if user_role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
                    raise PermissionDenied("매출 데이터 수정 권한이 없습니다.")
                    
            # 읽기 권한 확인
            elif permission_type == 'read':
                if not RevenuePermissionManager.has_revenue_access(request.user):
                    raise PermissionDenied("매출 데이터 조회 권한이 없습니다.")
                    
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

# Django 그룹 생성 유틸리티
def create_revenue_groups():
    """매출 관리 관련 Django 그룹 생성"""
    groups_to_create = [
        ('super_admin', '최고관리자'),
        ('admin', '관리자'), 
        ('middle_manager', '중간관리자'),
        ('team_member', '팀원'),
        ('partner', '파트너/도급사'),
        ('client', '고객'),
    ]
    
    created_groups = []
    for group_name, description in groups_to_create:
        group, created = Group.objects.get_or_create(name=group_name)
        if created:
            created_groups.append(f"{group_name} ({description})")
            
    return created_groups

# 사용자 역할 할당 유틸리티
def assign_user_role(user, role):
    """사용자에게 역할 할당"""
    if role not in UserRole.ALL_ROLES:
        raise ValueError(f"유효하지 않은 역할입니다: {role}")
        
    # 기존 그룹에서 제거
    user.groups.clear()
    
    # 새 그룹 할당
    try:
        group = Group.objects.get(name=role)
        user.groups.add(group)
        logger.info(f"사용자 {user.username}에게 {UserRole.ROLE_NAMES[role]} 역할 할당됨")
        return True
    except Group.DoesNotExist:
        logger.error(f"그룹 {role}이 존재하지 않습니다.")
        return False

def get_user_revenue_permissions(user):
    """사용자의 매출 관련 권한 정보 반환"""
    user_role = RevenuePermissionManager.get_user_role(user)
    
    permissions = {
        'role': user_role,
        'role_name': UserRole.ROLE_NAMES.get(user_role, '알 수 없음'),
        'can_view_all': user_role in [UserRole.SUPER_ADMIN, UserRole.ADMIN],
        'can_edit': user_role in [UserRole.SUPER_ADMIN, UserRole.ADMIN],
        'can_export': user_role in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MIDDLE_MANAGER],
        'data_masking_level': _get_masking_level(user_role)
    }
    
    return permissions

def _get_masking_level(user_role):
    """마스킹 레벨 반환"""
    masking_levels = {
        UserRole.SUPER_ADMIN: 'none',      # 마스킹 없음
        UserRole.ADMIN: 'none',            # 마스킹 없음  
        UserRole.MIDDLE_MANAGER: 'partial', # 부분 마스킹
        UserRole.TEAM_MEMBER: 'moderate',   # 중간 마스킹
        UserRole.PARTNER: 'high',          # 높은 마스킹
        UserRole.CLIENT: 'maximum',        # 최대 마스킹
    }
    
    return masking_levels.get(user_role, 'maximum')