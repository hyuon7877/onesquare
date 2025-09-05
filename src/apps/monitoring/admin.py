"""
모니터링 시스템 Django Admin 설정
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    SystemMetrics, RequestMetrics, UserActivity, 
    NotionAPIMetrics, ErrorLog, PerformanceAlert
)


@admin.register(SystemMetrics)
class SystemMetricsAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'cpu_percent', 'memory_percent', 'disk_usage_percent', 
                   'django_cpu_percent', 'django_memory_rss_mb']
    list_filter = ['timestamp']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    def has_add_permission(self, request):
        return False  # 자동 생성되는 데이터이므로 수동 추가 불가
    
    def has_change_permission(self, request, obj=None):
        return False  # 읽기 전용


@admin.register(RequestMetrics)
class RequestMetricsAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'method', 'path_short', 'status_code', 
                   'response_time_ms', 'user_link', 'ip_address']
    list_filter = ['method', 'status_code', 'timestamp']
    search_fields = ['path', 'user__username', 'ip_address']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    def path_short(self, obj):
        return obj.path[:50] + '...' if len(obj.path) > 50 else obj.path
    path_short.short_description = 'Path'
    
    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return 'Anonymous'
    user_link.short_description = 'User'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user_link', 'path_short', 'method', 
                   'status_code', 'duration_ms', 'is_authenticated']
    list_filter = ['method', 'status_code', 'is_authenticated', 'timestamp']
    search_fields = ['user__username', 'path', 'ip_address', 'session_key']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    def path_short(self, obj):
        return obj.path[:50] + '...' if len(obj.path) > 50 else obj.path
    path_short.short_description = 'Path'
    
    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return 'Anonymous'
    user_link.short_description = 'User'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(NotionAPIMetrics)
class NotionAPIMetricsAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'endpoint', 'method', 'status_badge', 
                   'response_time_ms', 'operation_type', 'user_link']
    list_filter = ['method', 'is_success', 'operation_type', 'timestamp']
    search_fields = ['endpoint', 'user__username', 'error_message']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    def status_badge(self, obj):
        if obj.is_success:
            return format_html('<span style="color: green;">✓ SUCCESS</span>')
        else:
            return format_html('<span style="color: red;">✗ FAILED</span>')
    status_badge.short_description = 'Status'
    
    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return '-'
    user_link.short_description = 'User'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ErrorLog)
class ErrorLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'error_type', 'level', 'message_short', 
                   'path', 'resolved_badge', 'user_link']
    list_filter = ['error_type', 'level', 'is_resolved', 'timestamp']
    search_fields = ['message', 'path', 'exception_type', 'user__username']
    readonly_fields = ['timestamp', 'extra_data']
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    actions = ['mark_as_resolved']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('timestamp', 'error_type', 'level', 'message')
        }),
        ('컨텍스트', {
            'fields': ('path', 'method', 'status_code', 'user', 'ip_address')
        }),
        ('기술 정보', {
            'fields': ('exception_type', 'stack_trace', 'extra_data')
        }),
        ('해결 상태', {
            'fields': ('is_resolved', 'resolved_at', 'resolved_by')
        }),
    )
    
    def message_short(self, obj):
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
    message_short.short_description = 'Message'
    
    def resolved_badge(self, obj):
        if obj.is_resolved:
            return format_html('<span style="color: green;">✓ Resolved</span>')
        else:
            return format_html('<span style="color: orange;">⚠ Open</span>')
    resolved_badge.short_description = 'Status'
    
    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return '-'
    user_link.short_description = 'User'
    
    def mark_as_resolved(self, request, queryset):
        for error in queryset:
            error.mark_resolved(user=request.user)
        self.message_user(request, f'{queryset.count()}개 에러가 해결됨으로 표시되었습니다.')
    mark_as_resolved.short_description = '선택한 에러를 해결됨으로 표시'


@admin.register(PerformanceAlert)
class PerformanceAlertAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'alert_type', 'severity_badge', 'message_short', 
                   'threshold_actual', 'acknowledged_badge']
    list_filter = ['alert_type', 'severity', 'is_acknowledged', 'timestamp']
    search_fields = ['message', 'related_path', 'related_user__username']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    actions = ['acknowledge_alerts']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('timestamp', 'alert_type', 'severity', 'message')
        }),
        ('메트릭 정보', {
            'fields': ('threshold_value', 'actual_value', 'related_path', 'related_user')
        }),
        ('확인 상태', {
            'fields': ('is_acknowledged', 'acknowledged_at', 'acknowledged_by')
        }),
    )
    
    def severity_badge(self, obj):
        colors = {
            'low': 'blue',
            'medium': 'orange', 
            'high': 'red',
            'critical': 'darkred'
        }
        color = colors.get(obj.severity, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.severity.upper()
        )
    severity_badge.short_description = 'Severity'
    
    def message_short(self, obj):
        return obj.message[:80] + '...' if len(obj.message) > 80 else obj.message
    message_short.short_description = 'Message'
    
    def threshold_actual(self, obj):
        if obj.threshold_value and obj.actual_value:
            return f'{obj.actual_value} / {obj.threshold_value}'
        return '-'
    threshold_actual.short_description = 'Actual / Threshold'
    
    def acknowledged_badge(self, obj):
        if obj.is_acknowledged:
            return format_html('<span style="color: green;">✓ Ack</span>')
        else:
            return format_html('<span style="color: red;">⚠ New</span>')
    acknowledged_badge.short_description = 'Status'
    
    def acknowledge_alerts(self, request, queryset):
        for alert in queryset:
            alert.acknowledge(user=request.user)
        self.message_user(request, f'{queryset.count()}개 알림이 확인됨으로 표시되었습니다.')
    acknowledge_alerts.short_description = '선택한 알림을 확인됨으로 표시'


# Admin 사이트 커스터마이징
admin.site.site_header = 'OneSquare 모니터링 시스템'
admin.site.site_title = 'OneSquare Monitoring'
admin.site.index_title = '시스템 모니터링 및 관리'