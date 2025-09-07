from django.contrib import admin
from .models import DashboardStatistics, ChartData, CalendarEvent
# Activity와 Notification은 collaboration.admin에서 관리


@admin.register(DashboardStatistics)
class DashboardStatisticsAdmin(admin.ModelAdmin):
    list_display = ('date', 'total_users', 'active_projects', 'completed_tasks', 'pending_reports')
    list_filter = ('date', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ['-date']


# Activity와 Notification admin은 collaboration 앱에서 관리
# 중복 제거를 위해 주석 처리

# @admin.register(Activity)
# class ActivityAdmin(admin.ModelAdmin):
#     list_display = ('user', 'activity_type', 'description', 'timestamp')
#     list_filter = ('activity_type', 'timestamp', 'user')
#     search_fields = ('user__username', 'description')
#     readonly_fields = ('timestamp',)
#     ordering = ['-timestamp']


# @admin.register(Notification)
# class NotificationAdmin(admin.ModelAdmin):
#     list_display = ('user', 'title', 'unread', 'timestamp')
#     list_filter = ('unread', 'timestamp')
#     search_fields = ('user__username', 'title', 'message')
#     readonly_fields = ('timestamp',)
#     ordering = ['-timestamp']


@admin.register(ChartData)
class ChartDataAdmin(admin.ModelAdmin):
    list_display = ('chart_type', 'date', 'created_at')
    list_filter = ('chart_type', 'date')
    readonly_fields = ('created_at',)
    ordering = ['-created_at']


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'event_type', 'start_date', 'end_date', 'organizer', 'is_public')
    list_filter = ('event_type', 'start_date', 'is_public', 'repeat')
    search_fields = ('title', 'description', 'location')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('participants',)
    date_hierarchy = 'start_date'
    ordering = ['-start_date']
