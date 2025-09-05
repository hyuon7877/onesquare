"""
OneSquare 사용자 인증 시스템 - Django Admin 설정
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group, Permission
from django.utils.html import format_html
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import path
from django.http import HttpResponse
from .models import CustomUser, OTPCode, UserSession, UserGroup, OTPToken
from .permissions import PermissionManager, SystemModule, PermissionLevel, PERMISSION_MATRIX


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """커스텀 사용자 관리자 페이지"""
    
    # 목록 페이지에 표시할 필드들
    list_display = [
        'username', 'email', 'user_type', 'auth_method', 'company', 
        'is_approved', 'is_active', 'last_login', 'created_at'
    ]
    
    # 필터링 옵션
    list_filter = [
        'user_type', 'auth_method', 'is_approved', 'is_active', 
        'is_staff', 'is_superuser', 'created_at'
    ]
    
    # 검색 가능한 필드들
    search_fields = ['username', 'email', 'first_name', 'last_name', 'company', 'phone_number']
    
    # 정렬 기준
    ordering = ['-created_at']
    
    # 상세 페이지 필드 구성
    fieldsets = (
        ('기본 정보', {
            'fields': ('username', 'email', 'first_name', 'last_name')
        }),
        ('사용자 분류', {
            'fields': ('user_type', 'auth_method', 'is_approved')
        }),
        ('연락처 정보', {
            'fields': ('phone_number', 'company', 'department', 'position')
        }),
        ('프로필', {
            'fields': ('profile_image',)
        }),
        ('권한', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('시스템 정보', {
            'fields': ('last_login', 'last_login_ip', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    # 사용자 추가 시 필드
    add_fieldsets = (
        ('기본 정보', {
            'fields': ('username', 'email', 'password1', 'password2')
        }),
        ('사용자 분류', {
            'fields': ('user_type', 'auth_method')
        }),
        ('연락처 정보', {
            'fields': ('phone_number', 'company', 'department', 'position')
        }),
    )
    
    # 읽기 전용 필드
    readonly_fields = ['last_login', 'date_joined', 'created_at', 'updated_at']
    
    # 액션 추가
    actions = ['approve_users', 'deactivate_users', 'activate_users']
    
    def approve_users(self, request, queryset):
        """사용자 승인 액션"""
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated}명의 사용자가 승인되었습니다.')
    approve_users.short_description = '선택된 사용자 승인'
    
    def deactivate_users(self, request, queryset):
        """사용자 비활성화 액션"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated}명의 사용자가 비활성화되었습니다.')
    deactivate_users.short_description = '선택된 사용자 비활성화'
    
    def activate_users(self, request, queryset):
        """사용자 활성화 액션"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated}명의 사용자가 활성화되었습니다.')
    activate_users.short_description = '선택된 사용자 활성화'


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    """OTP 코드 관리자 페이지"""
    
    list_display = [
        'user', 'code', 'delivery_target', 
        'is_used', 'is_expired_status', 'created_at'
    ]
    
    list_filter = ['is_used', 'created_at']
    
    search_fields = ['user__username', 'user__email', 'delivery_target']
    
    readonly_fields = ['created_at', 'used_at', 'is_expired_status']
    
    ordering = ['-created_at']
    
    def is_expired_status(self, obj):
        """만료 상태 표시"""
        if obj.is_expired:
            return format_html('<span style="color: red;">만료됨</span>')
        return format_html('<span style="color: green;">유효함</span>')
    is_expired_status.short_description = '만료 상태'
    
    # OTP 코드는 보안상 수정 불가
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_add_permission(self, request):
        return False


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """사용자 세션 관리자 페이지"""
    
    list_display = [
        'user', 'ip_address', 'is_active', 'is_expired_status', 
        'created_at', 'last_activity'
    ]
    
    list_filter = ['is_active', 'created_at', 'last_activity']
    
    search_fields = ['user__username', 'user__email', 'ip_address']
    
    readonly_fields = ['session_key', 'created_at', 'last_activity', 'is_expired_status']
    
    ordering = ['-last_activity']
    
    def is_expired_status(self, obj):
        """만료 상태 표시"""
        if obj.is_expired:
            return format_html('<span style="color: red;">만료됨</span>')
        return format_html('<span style="color: green;">활성</span>')
    is_expired_status.short_description = '만료 상태'
    
    actions = ['terminate_sessions']
    
    def terminate_sessions(self, request, queryset):
        """세션 강제 종료 액션"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated}개의 세션이 종료되었습니다.')
    terminate_sessions.short_description = '선택된 세션 강제 종료'


@admin.register(UserGroup)
class UserGroupAdmin(admin.ModelAdmin):
    """사용자 그룹 정보 관리자 페이지"""
    
    list_display = [
        'group', 'user_type', 'can_access_dashboard', 'can_manage_users',
        'can_view_reports', 'can_manage_calendar', 'can_access_field_reports'
    ]
    
    list_filter = [
        'user_type', 'can_access_dashboard', 'can_manage_users',
        'can_view_reports', 'can_manage_calendar', 'can_access_field_reports'
    ]
    
    search_fields = ['group__name', 'description']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('group', 'user_type', 'description')
        }),
        ('권한 설정', {
            'fields': (
                'can_access_dashboard', 'can_manage_users', 'can_view_reports',
                'can_manage_calendar', 'can_access_field_reports'
            )
        }),
        ('시스템 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(OTPToken)
class OTPTokenAdmin(admin.ModelAdmin):
    """OTP 토큰 관리자 페이지"""
    
    list_display = [
        'user', 'token', 'otp_type', 'destination', 'status',
        'attempt_count', 'max_attempts', 'is_expired_status', 'created_at'
    ]
    
    list_filter = [
        'otp_type', 'status', 
        'attempt_count', 'created_at', 'expires_at'
    ]
    
    search_fields = ['user__username', 'user__email', 'destination']
    
    readonly_fields = [
        'token', 'created_at', 'expires_at', 'verified_at', 
        'is_expired_status', 'remaining_time'
    ]
    
    ordering = ['-created_at']
    
    def is_expired_status(self, obj):
        """만료 상태 표시"""
        if obj.is_expired:
            return format_html('<span style="color: red;">만료됨</span>')
        return format_html('<span style="color: green;">유효함</span>')
    is_expired_status.short_description = '만료 상태'
    
    def remaining_time(self, obj):
        """남은 시간 표시"""
        if obj.is_expired:
            return "만료됨"
        remaining = (obj.expires_at - timezone.now()).total_seconds()
        if remaining > 0:
            minutes = int(remaining // 60)
            seconds = int(remaining % 60)
            return f"{minutes}분 {seconds}초"
        return "만료됨"
    remaining_time.short_description = '남은 시간'
    
    # OTP 토큰은 보안상 수정 제한
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_add_permission(self, request):
        return False


# 권한 관리 커스텀 관리자 페이지

class PermissionManagementAdmin:
    """권한 관리 전용 관리자 인터페이스"""
    
    def get_urls(self):
        """커스텀 URL 패턴 추가"""
        urls = super().get_urls() if hasattr(super(), 'get_urls') else []
        custom_urls = [
            path('permissions/matrix/', self.admin_site.admin_view(self.permission_matrix_view), 
                 name='auth_permission_matrix'),
            path('permissions/setup/', self.admin_site.admin_view(self.permission_setup_view), 
                 name='auth_permission_setup'),
            path('permissions/user/<int:user_id>/', self.admin_site.admin_view(self.user_permission_detail_view), 
                 name='auth_user_permission_detail'),
        ]
        return custom_urls + urls
    
    def permission_matrix_view(self, request):
        """권한 매트릭스 조회 페이지"""
        context = {
            'title': 'OneSquare 권한 매트릭스',
            'permission_matrix': PERMISSION_MATRIX,
            'system_modules': SystemModule,
            'permission_levels': PermissionLevel,
            'user_types': ['SUPER_ADMIN', 'MANAGER', 'TEAM_MEMBER', 'PARTNER', 'CONTRACTOR', 'CUSTOM']
        }
        
        return render(request, 'admin/auth_system/permission_matrix.html', context)
    
    def permission_setup_view(self, request):
        """권한 시스템 초기화 페이지"""
        if request.method == 'POST':
            action = request.POST.get('action')
            
            if action == 'setup_permissions':
                try:
                    from django.core.management import call_command
                    call_command('setup_permissions', force=True)
                    messages.success(request, '권한 시스템이 성공적으로 초기화되었습니다.')
                except Exception as e:
                    messages.error(request, f'권한 시스템 초기화 중 오류가 발생했습니다: {str(e)}')
            
            elif action == 'update_all_users':
                try:
                    updated_count = 0
                    for user in CustomUser.objects.all():
                        user.assign_user_type_permissions()
                        updated_count += 1
                    messages.success(request, f'{updated_count}명의 사용자 권한이 업데이트되었습니다.')
                except Exception as e:
                    messages.error(request, f'사용자 권한 업데이트 중 오류가 발생했습니다: {str(e)}')
            
            return redirect('admin:auth_permission_setup')
        
        # 시스템 상태 조회
        context = {
            'title': '권한 시스템 관리',
            'total_users': CustomUser.objects.count(),
            'total_groups': Group.objects.filter(name__startswith='OneSquare_').count(),
            'total_permissions': Permission.objects.count(),
            'user_type_stats': {
                user_type[1]: CustomUser.objects.filter(user_type=user_type[0]).count()
                for user_type in CustomUser._meta.get_field('user_type').choices
            }
        }
        
        return render(request, 'admin/auth_system/permission_setup.html', context)
    
    def user_permission_detail_view(self, request, user_id):
        """개별 사용자 권한 상세 조회"""
        try:
            user = CustomUser.objects.get(id=user_id)
            
            context = {
                'title': f'{user.username} 권한 상세',
                'user': user,
                'user_permissions': user.get_permission_summary(),
                'accessible_modules': user.get_accessible_modules(),
                'user_groups': user.groups.all(),
                'individual_permissions': user.user_permissions.all(),
            }
            
            return render(request, 'admin/auth_system/user_permission_detail.html', context)
            
        except CustomUser.DoesNotExist:
            messages.error(request, '존재하지 않는 사용자입니다.')
            return redirect('admin:auth_system_customuser_changelist')


# 기존 CustomUserAdmin 업데이트
CustomUserAdmin.list_display = [
    'username', 'email', 'user_type_display', 'auth_method', 'company', 
    'is_approved', 'is_active', 'last_login', 'permission_summary_display', 'created_at'
]

def user_type_display(self, obj):
    """사용자 타입 한글 표시"""
    return obj.get_user_type_display()
user_type_display.short_description = '사용자 타입'

def permission_summary_display(self, obj):
    """권한 요약 표시"""
    accessible_modules = obj.get_accessible_modules()
    if len(accessible_modules) > 3:
        return f"{len(accessible_modules)}개 모듈 접근 가능"
    elif accessible_modules:
        module_names = [module.value.replace('_', ' ').title() for module in accessible_modules[:3]]
        return ', '.join(module_names)
    else:
        return "접근 권한 없음"
permission_summary_display.short_description = '권한 요약'

# 메서드를 클래스에 추가
CustomUserAdmin.user_type_display = user_type_display
CustomUserAdmin.permission_summary_display = permission_summary_display

# 액션 추가
def approve_users(modeladmin, request, queryset):
    """사용자 승인 액션"""
    updated = queryset.update(is_approved=True)
    messages.success(request, f'{updated}명의 사용자를 승인했습니다.')
approve_users.short_description = '선택된 사용자 승인'

def assign_permissions(modeladmin, request, queryset):
    """권한 할당 액션"""
    updated = 0
    for user in queryset:
        user.assign_user_type_permissions()
        updated += 1
    messages.success(request, f'{updated}명의 사용자 권한을 업데이트했습니다.')
assign_permissions.short_description = '사용자 타입에 따른 권한 할당'

CustomUserAdmin.actions = ['approve_users', 'assign_permissions']
CustomUserAdmin.actions[0] = approve_users
CustomUserAdmin.actions[1] = assign_permissions

def invalidate_tokens(self, request, queryset):
    """토큰 무효화 액션"""
    updated = queryset.update(status='used')
    self.message_user(request, f'{updated}개의 OTP 토큰이 무효화되었습니다.')
invalidate_tokens.short_description = '선택된 토큰 무효화'

OTPTokenAdmin.actions = ['invalidate_tokens']
OTPTokenAdmin.fieldsets = (
    ('토큰 정보', {
        'fields': ('user', 'token', 'otp_type', 'destination')
    }),
    ('상태', {
        'fields': ('status', 'attempt_count', 'max_attempts')
    }),
    ('시간 정보', {
        'fields': ('created_at', 'expires_at', 'verified_at', 'is_expired_status', 'remaining_time')
    }),
    ('추가 정보', {
        'fields': ('ip_address', 'user_agent'),
        'classes': ('collapse',)
    }),
)


# Django Admin 사이트 설정 커스터마이징
admin.site.site_header = "OneSquare 관리자"
admin.site.site_title = "OneSquare Admin"
admin.site.index_title = "OneSquare 시스템 관리"