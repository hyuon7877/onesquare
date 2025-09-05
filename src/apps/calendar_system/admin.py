"""
OneSquare 통합 캘린더 시스템 - Django Admin 설정
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import path
from django.http import JsonResponse
from .models import (
    CalendarCategory, CalendarEvent, EventAttendee, 
    EventReminder, CalendarSettings, NotionCalendarSync
)


@admin.register(CalendarCategory)
class CalendarCategoryAdmin(admin.ModelAdmin):
    """캘린더 카테고리 관리자"""
    
    list_display = [
        'name', 'color_display', 'accessible_user_types_display', 
        'is_active', 'created_at'
    ]
    
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('name', 'color', 'description', 'is_active')
        }),
        ('권한 설정', {
            'fields': ('accessible_user_types',),
            'description': '접근 가능한 사용자 타입을 JSON 배열로 입력 (예: ["SUPER_ADMIN", "MANAGER"])'
        }),
    )
    
    def color_display(self, obj):
        """색상 미리보기"""
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc; border-radius: 3px;"></div>',
            obj.color
        )
    color_display.short_description = '색상'
    
    def accessible_user_types_display(self, obj):
        """접근 가능한 사용자 타입 표시"""
        if not obj.accessible_user_types:
            return '모든 사용자'
        return ', '.join(obj.accessible_user_types)
    accessible_user_types_display.short_description = '접근 권한'


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    """캘린더 이벤트 관리자"""
    
    list_display = [
        'title', 'creator', 'category', 'event_type', 'priority',
        'start_datetime', 'end_datetime', 'attendee_count', 
        'notion_sync_status', 'is_active'
    ]
    
    list_filter = [
        'event_type', 'priority', 'category', 'is_active', 
        'start_datetime', 'created_at', 'recurrence_type'
    ]
    
    search_fields = ['title', 'description', 'creator__username', 'location']
    
    date_hierarchy = 'start_datetime'
    ordering = ['-start_datetime']
    
    filter_horizontal = []  # attendees는 through 모델이므로 별도 처리
    
    readonly_fields = ['created_at', 'updated_at', 'last_synced_at', 'duration_display']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('title', 'description', 'creator', 'category')
        }),
        ('일정 시간', {
            'fields': (
                'start_datetime', 'end_datetime', 'is_all_day', 
                'duration_display', 'recurrence_type', 'recurrence_end_date'
            )
        }),
        ('이벤트 속성', {
            'fields': ('event_type', 'priority', 'location', 'url')
        }),
        ('알림 설정', {
            'fields': ('reminder_minutes',)
        }),
        ('Notion 연동', {
            'fields': ('notion_page_id', 'notion_database_id', 'last_synced_at'),
            'classes': ('collapse',)
        }),
        ('시스템 정보', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['sync_to_notion', 'duplicate_events', 'send_reminders']
    
    def attendee_count(self, obj):
        """참석자 수"""
        return obj.attendees.count()
    attendee_count.short_description = '참석자 수'
    
    def duration_display(self, obj):
        """이벤트 지속 시간 표시"""
        return f"{obj.duration_minutes}분"
    duration_display.short_description = '지속 시간'
    
    def notion_sync_status(self, obj):
        """Notion 동기화 상태"""
        if obj.notion_page_id:
            if obj.last_synced_at:
                time_diff = timezone.now() - obj.last_synced_at
                if time_diff.days > 1:
                    return format_html('<span style="color: orange;">오래됨</span>')
                else:
                    return format_html('<span style="color: green;">동기화됨</span>')
            else:
                return format_html('<span style="color: red;">미동기화</span>')
        return format_html('<span style="color: gray;">미연결</span>')
    notion_sync_status.short_description = 'Notion 상태'
    
    def sync_to_notion(self, request, queryset):
        """Notion 동기화 액션"""
        try:
            from .notion_sync import NotionCalendarService
            service = NotionCalendarService()
            
            success_count = 0
            for event in queryset:
                if service.sync_event_to_notion(event):
                    success_count += 1
            
            self.message_user(
                request, 
                f'{success_count}개의 이벤트를 Notion에 동기화했습니다.',
                messages.SUCCESS
            )
        except Exception as e:
            self.message_user(
                request, 
                f'Notion 동기화 중 오류 발생: {str(e)}',
                messages.ERROR
            )
    sync_to_notion.short_description = '선택된 이벤트를 Notion에 동기화'
    
    def duplicate_events(self, request, queryset):
        """이벤트 복제 액션"""
        duplicated = 0
        for event in queryset:
            event.pk = None
            event.title += ' (복사본)'
            event.notion_page_id = ''
            event.last_synced_at = None
            event.save()
            duplicated += 1
        
        self.message_user(request, f'{duplicated}개의 이벤트를 복제했습니다.')
    duplicate_events.short_description = '선택된 이벤트 복제'
    
    def send_reminders(self, request, queryset):
        """알림 전송 액션"""
        from .tasks import send_event_reminders
        
        reminder_count = 0
        for event in queryset:
            # 이벤트가 미래이고 활성화된 경우에만 알림 생성
            if event.start_datetime > timezone.now() and event.is_active:
                send_event_reminders(event.id)
                reminder_count += 1
        
        self.message_user(request, f'{reminder_count}개의 이벤트에 대한 알림을 예약했습니다.')
    send_reminders.short_description = '선택된 이벤트 알림 전송'


@admin.register(EventAttendee)
class EventAttendeeAdmin(admin.ModelAdmin):
    """이벤트 참석자 관리자"""
    
    list_display = [
        'event', 'user', 'status', 'response_at', 'created_at'
    ]
    
    list_filter = ['status', 'response_at', 'created_at']
    
    search_fields = [
        'event__title', 'user__username', 'user__email', 'notes'
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('event', 'user')


@admin.register(EventReminder)
class EventReminderAdmin(admin.ModelAdmin):
    """이벤트 알림 관리자"""
    
    list_display = [
        'event', 'user', 'reminder_datetime', 'status', 
        'notification_method', 'sent_at'
    ]
    
    list_filter = [
        'status', 'notification_method', 'reminder_datetime', 'sent_at'
    ]
    
    search_fields = ['event__title', 'user__username']
    
    readonly_fields = ['sent_at', 'created_at']
    
    actions = ['resend_reminders', 'mark_as_sent']
    
    def resend_reminders(self, request, queryset):
        """알림 재전송"""
        queryset.update(status=EventReminder.Status.PENDING, sent_at=None)
        self.message_user(request, f'{queryset.count()}개의 알림을 재전송 대기열에 추가했습니다.')
    resend_reminders.short_description = '선택된 알림 재전송'
    
    def mark_as_sent(self, request, queryset):
        """알림 전송 완료 처리"""
        queryset.update(status=EventReminder.Status.SENT, sent_at=timezone.now())
        self.message_user(request, f'{queryset.count()}개의 알림을 전송 완료로 표시했습니다.')
    mark_as_sent.short_description = '선택된 알림을 전송 완료로 표시'


@admin.register(CalendarSettings)
class CalendarSettingsAdmin(admin.ModelAdmin):
    """캘린더 설정 관리자"""
    
    list_display = [
        'user', 'default_view', 'work_time_display', 
        'email_notifications', 'push_notifications', 'updated_at'
    ]
    
    list_filter = [
        'default_view', 'email_notifications', 'push_notifications', 
        'show_weekends', 'updated_at'
    ]
    
    search_fields = ['user__username', 'user__email']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('사용자', {
            'fields': ('user',)
        }),
        ('뷰 설정', {
            'fields': ('default_view', 'show_weekends', 'show_declined_events')
        }),
        ('업무 시간', {
            'fields': ('work_start_time', 'work_end_time')
        }),
        ('알림 설정', {
            'fields': (
                'default_reminder_minutes', 'email_notifications', 
                'push_notifications'
            )
        }),
        ('필터 설정', {
            'fields': ('visible_categories',),
            'description': '표시할 카테고리 ID를 JSON 배열로 입력'
        }),
        ('시스템 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def work_time_display(self, obj):
        """업무 시간 표시"""
        return f"{obj.work_start_time} - {obj.work_end_time}"
    work_time_display.short_description = '업무 시간'


@admin.register(NotionCalendarSync)
class NotionCalendarSyncAdmin(admin.ModelAdmin):
    """Notion 동기화 로그 관리자"""
    
    list_display = [
        'event', 'sync_type', 'status', 'execution_time_display', 
        'executed_at', 'notion_page_id'
    ]
    
    list_filter = [
        'sync_type', 'status', 'executed_at'
    ]
    
    search_fields = [
        'event__title', 'notion_page_id', 'error_message'
    ]
    
    readonly_fields = [
        'executed_at', 'execution_time_ms', 'request_data', 
        'response_data', 'error_message'
    ]
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('event', 'sync_type', 'status', 'notion_page_id')
        }),
        ('실행 정보', {
            'fields': ('executed_at', 'execution_time_ms')
        }),
        ('데이터', {
            'fields': ('request_data', 'response_data', 'error_message'),
            'classes': ('collapse',)
        }),
    )
    
    def execution_time_display(self, obj):
        """실행 시간 표시"""
        if obj.execution_time_ms:
            return f"{obj.execution_time_ms}ms"
        return '-'
    execution_time_display.short_description = '실행 시간'
    
    def has_add_permission(self, request):
        """추가 권한 제한 (로그는 시스템에서 자동 생성)"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """수정 권한 제한"""
        return False


# 대시보드 커스터마이징
class CalendarDashboardMixin:
    """캘린더 대시보드 관련 기능"""
    
    def get_urls(self):
        urls = super().get_urls() if hasattr(super(), 'get_urls') else []
        custom_urls = [
            path(
                'calendar/dashboard/',
                self.admin_site.admin_view(self.calendar_dashboard_view),
                name='calendar_dashboard'
            ),
            path(
                'calendar/stats/',
                self.admin_site.admin_view(self.calendar_stats_view),
                name='calendar_stats'
            ),
        ]
        return custom_urls + urls
    
    def calendar_dashboard_view(self, request):
        """캘린더 대시보드"""
        from django.db.models import Count, Q
        from datetime import datetime, timedelta
        
        today = timezone.now().date()
        this_month = today.replace(day=1)
        next_month = (this_month + timedelta(days=32)).replace(day=1)
        
        # 통계 계산
        stats = {
            'total_events': CalendarEvent.objects.filter(is_active=True).count(),
            'today_events': CalendarEvent.objects.filter(
                start_datetime__date=today, is_active=True
            ).count(),
            'this_month_events': CalendarEvent.objects.filter(
                start_datetime__gte=this_month,
                start_datetime__lt=next_month,
                is_active=True
            ).count(),
            'upcoming_events': CalendarEvent.objects.filter(
                start_datetime__gt=timezone.now(),
                is_active=True
            ).count(),
        }
        
        # 카테고리별 이벤트 수
        category_stats = CalendarCategory.objects.annotate(
            event_count=Count('calendarevent', filter=Q(calendarevent__is_active=True))
        ).order_by('-event_count')[:5]
        
        # 최근 이벤트
        recent_events = CalendarEvent.objects.filter(is_active=True).order_by('-created_at')[:10]
        
        context = {
            'title': '캘린더 대시보드',
            'stats': stats,
            'category_stats': category_stats,
            'recent_events': recent_events,
        }
        
        return render(request, 'admin/calendar_system/dashboard.html', context)
    
    def calendar_stats_view(self, request):
        """캘린더 통계 API"""
        from django.db.models import Count, Q
        from datetime import datetime, timedelta
        
        # 월별 이벤트 통계 (최근 12개월)
        monthly_stats = []
        for i in range(12):
            month_start = (timezone.now().replace(day=1) - timedelta(days=30*i)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1)
            
            count = CalendarEvent.objects.filter(
                start_datetime__gte=month_start,
                start_datetime__lt=month_end,
                is_active=True
            ).count()
            
            monthly_stats.append({
                'month': month_start.strftime('%Y-%m'),
                'count': count
            })
        
        return JsonResponse({
            'monthly_stats': list(reversed(monthly_stats))
        })


# CalendarEventAdmin에 대시보드 기능 추가
CalendarEventAdmin.__bases__ = (CalendarDashboardMixin,) + CalendarEventAdmin.__bases__