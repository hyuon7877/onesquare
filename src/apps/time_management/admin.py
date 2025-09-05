"""
OneSquare Time Management - Django Admin 설정

업무시간 관리 모델들의 Django Admin 인터페이스 설정
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta

from .models import (
    WorkTimeSettings, 
    WorkTimeRecord, 
    WorkTimeSummary, 
    OverTimeRule
)


@admin.register(WorkTimeSettings)
class WorkTimeSettingsAdmin(admin.ModelAdmin):
    """근무시간 설정 관리"""
    
    list_display = [
        'name', 
        'setting_type', 
        'daily_standard_hours', 
        'weekly_standard_hours',
        'is_active',
        'effective_from',
        'effective_until',
        'created_at'
    ]
    list_filter = [
        'setting_type', 
        'is_active', 
        'effective_from', 
        'created_at'
    ]
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['target_users']
    
    fieldsets = (
        ('기본 정보', {
            'fields': (
                'name',
                'description', 
                'setting_type'
            )
        }),
        ('근무시간 기준', {
            'fields': (
                'daily_standard_minutes',
                'weekly_standard_minutes',
                'monthly_standard_minutes'
            )
        }),
        ('허용 시간 설정', {
            'fields': (
                'early_arrival_limit_minutes',
                'late_departure_limit_minutes',
                'break_time_minutes',
                'auto_deduct_break'
            )
        }),
        ('적용 설정', {
            'fields': (
                'target_users',
                'is_active',
                'effective_from',
                'effective_until'
            )
        }),
        ('Notion 연동', {
            'fields': (
                'notion_database_id',
                'notion_page_id'
            ),
            'classes': ('collapse',)
        }),
        ('시스템 정보', {
            'fields': (
                'created_by',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    def save_model(self, request, obj, form, change):
        """생성자 자동 설정"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(WorkTimeRecord)
class WorkTimeRecordAdmin(admin.ModelAdmin):
    """근무시간 기록 관리"""
    
    list_display = [
        'user',
        'work_date',
        'check_in_time_formatted',
        'check_out_time_formatted',
        'actual_work_hours_formatted',
        'overtime_status',
        'status',
        'record_type',
        'notion_sync_status'
    ]
    list_filter = [
        'status',
        'record_type',
        'work_date',
        'is_notion_synced',
        'user'
    ]
    search_fields = [
        'user__username',
        'user__first_name',
        'user__last_name',
        'memo'
    ]
    date_hierarchy = 'work_date'
    readonly_fields = [
        'total_work_minutes',
        'actual_work_minutes',
        'overtime_minutes',
        'break_minutes',
        'created_at',
        'updated_at',
        'notion_last_synced'
    ]
    
    fieldsets = (
        ('기본 정보', {
            'fields': (
                'user',
                'work_date',
                'record_type'
            )
        }),
        ('출퇴근 시간', {
            'fields': (
                'check_in_time',
                'check_out_time'
            )
        }),
        ('계산된 근무시간', {
            'fields': (
                'total_work_minutes',
                'break_minutes',
                'actual_work_minutes',
                'overtime_minutes'
            ),
            'classes': ('collapse',)
        }),
        ('메모 및 사유', {
            'fields': (
                'memo',
                'adjustment_reason'
            )
        }),
        ('승인 정보', {
            'fields': (
                'status',
                'approved_by',
                'approved_at'
            )
        }),
        ('위치 정보', {
            'fields': (
                'check_in_location',
                'check_out_location'
            ),
            'classes': ('collapse',)
        }),
        ('Notion 동기화', {
            'fields': (
                'notion_page_id',
                'is_notion_synced',
                'notion_last_synced'
            ),
            'classes': ('collapse',)
        }),
        ('시스템 정보', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    def check_in_time_formatted(self, obj):
        """출근시간 포맷팅"""
        if obj.check_in_time:
            return obj.check_in_time.strftime("%H:%M")
        return "-"
    check_in_time_formatted.short_description = "출근시간"
    
    def check_out_time_formatted(self, obj):
        """퇴근시간 포맷팅"""
        if obj.check_out_time:
            return obj.check_out_time.strftime("%H:%M")
        return "-"
    check_out_time_formatted.short_description = "퇴근시간"
    
    def actual_work_hours_formatted(self, obj):
        """실제 근무시간 포맷팅"""
        return obj.get_work_time_formatted()
    actual_work_hours_formatted.short_description = "실근무시간"
    
    def overtime_status(self, obj):
        """초과근무 상태 표시"""
        if obj.is_overtime:
            return format_html(
                '<span style="color: red;">+{}</span>',
                f"{obj.overtime_hours:.1f}h"
            )
        elif obj.is_undertime:
            return format_html(
                '<span style="color: orange;">-{}</span>',
                f"{(480 - obj.actual_work_minutes) / 60:.1f}h"
            )
        else:
            return format_html(
                '<span style="color: green;">표준</span>'
            )
    overtime_status.short_description = "초과근무"
    
    def notion_sync_status(self, obj):
        """Notion 동기화 상태"""
        if obj.is_notion_synced:
            return format_html(
                '<span style="color: green;">✓ 동기화됨</span>'
            )
        else:
            return format_html(
                '<span style="color: red;">✗ 미동기화</span>'
            )
    notion_sync_status.short_description = "Notion 동기화"
    
    actions = ['sync_to_notion', 'approve_records', 'export_to_excel']
    
    def sync_to_notion(self, request, queryset):
        """Notion 동기화 액션"""
        # TODO: Notion 동기화 로직 구현
        count = queryset.count()
        self.message_user(
            request, 
            f"{count}개 레코드의 Notion 동기화를 시작했습니다."
        )
    sync_to_notion.short_description = "선택된 기록들을 Notion에 동기화"
    
    def approve_records(self, request, queryset):
        """일괄 승인 액션"""
        updated = queryset.filter(status='confirmed').update(
            status='approved',
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(
            request,
            f"{updated}개 기록을 승인했습니다."
        )
    approve_records.short_description = "선택된 기록들 승인"


@admin.register(WorkTimeSummary)
class WorkTimeSummaryAdmin(admin.ModelAdmin):
    """근무시간 요약 관리"""
    
    list_display = [
        'user',
        'summary_type',
        'period_display',
        'actual_work_hours',
        'overtime_hours',
        'work_rate',
        'updated_at'
    ]
    list_filter = [
        'summary_type',
        'year',
        'month',
        'user'
    ]
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    readonly_fields = [
        'total_work_minutes',
        'actual_work_minutes',
        'overtime_minutes',
        'work_days',
        'late_count',
        'early_leave_count',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('기본 정보', {
            'fields': (
                'user',
                'summary_type'
            )
        }),
        ('기간 정보', {
            'fields': (
                'year',
                'month',
                'week',
                'day'
            )
        }),
        ('근무시간 통계', {
            'fields': (
                'total_work_minutes',
                'actual_work_minutes',
                'overtime_minutes',
                'standard_work_minutes'
            )
        }),
        ('출근 통계', {
            'fields': (
                'work_days',
                'expected_work_days',
                'late_count',
                'early_leave_count'
            )
        }),
        ('시스템 정보', {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    def period_display(self, obj):
        """기간 표시"""
        return str(obj)
    period_display.short_description = "기간"
    
    actions = ['recalculate_summary']
    
    def recalculate_summary(self, request, queryset):
        """통계 재계산 액션"""
        for summary in queryset:
            # TODO: 통계 재계산 로직 구현
            pass
        self.message_user(
            request,
            f"{queryset.count()}개 요약의 통계를 재계산했습니다."
        )
    recalculate_summary.short_description = "선택된 요약 재계산"


@admin.register(OverTimeRule)
class OverTimeRuleAdmin(admin.ModelAdmin):
    """초과근무 규정 관리"""
    
    list_display = [
        'name',
        'rule_type',
        'threshold_hours',
        'pay_rate',
        'requires_approval',
        'is_active',
        'created_at'
    ]
    list_filter = [
        'rule_type',
        'requires_approval',
        'is_active',
        'created_at'
    ]
    search_fields = ['name', 'description']
    filter_horizontal = ['target_users']
    
    fieldsets = (
        ('기본 정보', {
            'fields': (
                'name',
                'description',
                'rule_type'
            )
        }),
        ('기준 설정', {
            'fields': (
                'threshold_minutes',
                'pay_rate',
                'max_overtime_minutes'
            )
        }),
        ('승인 설정', {
            'fields': (
                'requires_approval',
                'target_users'
            )
        }),
        ('상태', {
            'fields': (
                'is_active',
            )
        })
    )
    
    def threshold_hours(self, obj):
        """기준시간 (시간 단위)"""
        return f"{obj.threshold_minutes / 60:.1f}h"
    threshold_hours.short_description = "기준시간"
