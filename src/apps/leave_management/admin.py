from django.contrib import admin
from django.utils.html import format_html
from .models import LeaveType, LeaveBalance, LeaveRequest, Holiday


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'max_days', 'requires_approval', 'created_at']
    list_filter = ['requires_approval', 'created_at']
    search_fields = ['name', 'description']


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ['user', 'year', 'total_annual_days', 'used_annual_days', 
                   'remaining_annual_days', 'carry_over_days', 'notion_sync_status']
    list_filter = ['year', 'notion_sync_status']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['remaining_annual_days', 'last_synced_at', 'created_at', 'updated_at']
    
    fieldsets = (
        ('사용자 정보', {
            'fields': ('user', 'year')
        }),
        ('연차 정보', {
            'fields': ('total_annual_days', 'used_annual_days', 'remaining_annual_days', 'carry_over_days')
        }),
        ('Notion 동기화', {
            'fields': ('notion_database_id', 'notion_sync_status', 'last_synced_at')
        }),
        ('메타데이터', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # 관리자만 추가 가능
        return request.user.is_superuser


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'leave_type', 'start_date', 'end_date', 'total_days', 
                   'status_badge', 'approver', 'created_at']
    list_filter = ['status', 'leave_type', 'start_date', 'created_at']
    search_fields = ['user__username', 'user__email', 'reason']
    readonly_fields = ['total_days', 'approved_at', 'created_at', 'updated_at', 
                      'notion_sync_status', 'last_synced_at']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('신청자 정보', {
            'fields': ('user', 'leave_type', 'emergency_contact')
        }),
        ('연차 기간', {
            'fields': ('start_date', 'end_date', 'is_half_day_start', 'is_half_day_end', 'total_days')
        }),
        ('신청 상세', {
            'fields': ('reason', 'attachment')
        }),
        ('승인 정보', {
            'fields': ('status', 'approver', 'approved_at', 'rejection_reason')
        }),
        ('Notion 동기화', {
            'fields': ('notion_page_id', 'notion_sync_status', 'last_synced_at'),
            'classes': ('collapse',)
        }),
        ('오프라인 지원', {
            'fields': ('is_offline_created', 'offline_sync_data'),
            'classes': ('collapse',)
        }),
        ('메타데이터', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': '#FFA500',
            'approved': '#008000',
            'rejected': '#FF0000',
            'cancelled': '#808080'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#000000'),
            obj.get_status_display()
        )
    status_badge.short_description = '상태'
    
    actions = ['approve_requests', 'reject_requests']
    
    def approve_requests(self, request, queryset):
        """선택한 연차 신청 승인"""
        for leave_request in queryset.filter(status='pending'):
            try:
                leave_request.approve(request.user)
                self.message_user(request, f'{leave_request.user}의 연차 신청이 승인되었습니다.')
            except Exception as e:
                self.message_user(request, f'{leave_request.user}의 연차 승인 실패: {str(e)}', level='ERROR')
    approve_requests.short_description = '선택한 연차 승인'
    
    def reject_requests(self, request, queryset):
        """선택한 연차 신청 반려"""
        for leave_request in queryset.filter(status='pending'):
            leave_request.reject(request.user, "관리자 일괄 반려")
            self.message_user(request, f'{leave_request.user}의 연차 신청이 반려되었습니다.')
    reject_requests.short_description = '선택한 연차 반려'


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ['date', 'name', 'is_public_holiday', 'is_company_holiday']
    list_filter = ['is_public_holiday', 'is_company_holiday', 'date']
    search_fields = ['name', 'description']
    ordering = ['date']
    
    fieldsets = (
        ('휴일 정보', {
            'fields': ('date', 'name', 'description')
        }),
        ('휴일 유형', {
            'fields': ('is_public_holiday', 'is_company_holiday')
        }),
        ('Notion 동기화', {
            'fields': ('notion_page_id',),
            'classes': ('collapse',)
        }),
        ('메타데이터', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
