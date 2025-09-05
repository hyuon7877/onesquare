"""
OneSquare Notion API 연동 - Django Admin 설정

이 모듈은 Notion API 관련 모델들의 Django Admin 인터페이스를 설정합니다.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Q
from .models import NotionDatabase, NotionPage, SyncHistory, NotionWebhook
from .services import NotionSyncService


@admin.register(NotionDatabase)
class NotionDatabaseAdmin(admin.ModelAdmin):
    """Notion 데이터베이스 관리"""
    
    list_display = [
        'title', 'database_type', 'is_active', 'pages_count', 
        'last_synced', 'is_synced_recently', 'created_by', 'created_at'
    ]
    list_filter = ['database_type', 'is_active', 'created_at', 'last_synced']
    search_fields = ['title', 'description', 'notion_id']
    readonly_fields = [
        'notion_id', 'created_at', 'updated_at', 'last_synced', 
        'schema_display', 'sync_status_display'
    ]
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('notion_id', 'title', 'description', 'database_type')
        }),
        ('동기화 설정', {
            'fields': ('is_active', 'sync_interval', 'last_synced')
        }),
        ('스키마 정보', {
            'fields': ('schema_display',),
            'classes': ('collapse',)
        }),
        ('동기화 상태', {
            'fields': ('sync_status_display',),
            'classes': ('collapse',)
        }),
        ('메타데이터', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by').annotate(
            pages_count=Count('pages', filter=Q(pages__status='active'))
        )
    
    def pages_count(self, obj):
        """페이지 수"""
        return obj.pages_count
    pages_count.short_description = '페이지 수'
    
    def schema_display(self, obj):
        """스키마 정보 표시"""
        if not obj.schema:
            return "스키마 없음"
        
        properties = obj.schema.get('properties', {})
        if not properties:
            return "속성 없음"
        
        html = "<ul>"
        for prop_name, prop_config in properties.items():
            prop_type = prop_config.get('type', 'unknown')
            html += f"<li><strong>{prop_name}</strong>: {prop_type}</li>"
        html += "</ul>"
        
        return format_html(html)
    schema_display.short_description = '스키마'
    
    def sync_status_display(self, obj):
        """동기화 상태 표시"""
        last_sync = obj.sync_history.order_by('-started_at').first()
        if not last_sync:
            return "동기화 기록 없음"
        
        status_colors = {
            'completed': '#28a745',
            'failed': '#dc3545',
            'in_progress': '#ffc107',
            'started': '#17a2b8'
        }
        
        color = status_colors.get(last_sync.status, '#6c757d')
        
        return format_html(
            '<div style="color: {};">'
            '<strong>{}</strong><br>'
            '시작: {}<br>'
            '처리: {}개 페이지<br>'
            '성공률: {:.1f}%'
            '</div>',
            color,
            last_sync.get_status_display(),
            last_sync.started_at.strftime('%Y-%m-%d %H:%M'),
            last_sync.total_pages,
            last_sync.success_rate
        )
    sync_status_display.short_description = '최근 동기화 상태'
    
    actions = ['sync_databases', 'refresh_schemas', 'activate_databases', 'deactivate_databases']
    
    def sync_databases(self, request, queryset):
        """선택된 데이터베이스 동기화"""
        sync_service = NotionSyncService()
        success_count = 0
        
        for database in queryset.filter(is_active=True):
            try:
                result = sync_service.sync_database(database, 'manual', request.user)
                if result.success:
                    success_count += 1
            except Exception as e:
                pass
        
        self.message_user(
            request, 
            f'{success_count}개 데이터베이스가 동기화되었습니다.'
        )
    sync_databases.short_description = '선택된 데이터베이스 동기화'
    
    def refresh_schemas(self, request, queryset):
        """스키마 새로고침"""
        from .services import NotionClient
        
        client = NotionClient()
        success_count = 0
        
        for database in queryset:
            try:
                notion_db = client.get_database(database.notion_id)
                new_schema = {
                    'properties': notion_db.get('properties', {}),
                    'title': notion_db.get('title', []),
                    'description': notion_db.get('description', [])
                }
                database.update_schema(new_schema)
                success_count += 1
            except Exception as e:
                pass
        
        self.message_user(
            request, 
            f'{success_count}개 데이터베이스의 스키마가 새로고침되었습니다.'
        )
    refresh_schemas.short_description = '스키마 새로고침'
    
    def activate_databases(self, request, queryset):
        """데이터베이스 활성화"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count}개 데이터베이스가 활성화되었습니다.')
    activate_databases.short_description = '선택된 데이터베이스 활성화'
    
    def deactivate_databases(self, request, queryset):
        """데이터베이스 비활성화"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count}개 데이터베이스가 비활성화되었습니다.')
    deactivate_databases.short_description = '선택된 데이터베이스 비활성화'


@admin.register(NotionPage)
class NotionPageAdmin(admin.ModelAdmin):
    """Notion 페이지 관리"""
    
    list_display = [
        'title', 'database', 'status', 'is_dirty', 'has_conflicts',
        'notion_last_edited_time', 'created_at'
    ]
    list_filter = [
        'status', 'is_dirty', 'database', 'notion_created_time', 'notion_last_edited_time'
    ]
    search_fields = ['title', 'notion_id']
    readonly_fields = [
        'notion_id', 'notion_created_time', 'notion_last_edited_time',
        'notion_created_by', 'notion_last_edited_by', 'local_hash',
        'created_at', 'updated_at', 'properties_display', 'conflicts_display'
    ]
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('database', 'title', 'status')
        }),
        ('Notion 메타데이터', {
            'fields': (
                'notion_id', 'notion_created_time', 'notion_last_edited_time',
                'notion_created_by', 'notion_last_edited_by'
            ),
            'classes': ('collapse',)
        }),
        ('동기화 정보', {
            'fields': ('is_dirty', 'local_hash', 'conflicts_display'),
            'classes': ('collapse',)
        }),
        ('속성 데이터', {
            'fields': ('properties_display',),
            'classes': ('collapse',)
        }),
        ('메타데이터', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def has_conflicts(self, obj):
        """충돌 여부"""
        return len(obj.sync_conflicts) > 0
    has_conflicts.boolean = True
    has_conflicts.short_description = '충돌'
    
    def properties_display(self, obj):
        """속성 데이터 표시"""
        if not obj.properties:
            return "속성 없음"
        
        html = "<ul>"
        for prop_name, prop_data in obj.properties.items():
            prop_type = prop_data.get('type', 'unknown')
            html += f"<li><strong>{prop_name}</strong> ({prop_type})</li>"
        html += "</ul>"
        
        return format_html(html)
    properties_display.short_description = '속성'
    
    def conflicts_display(self, obj):
        """충돌 정보 표시"""
        if not obj.sync_conflicts:
            return "충돌 없음"
        
        html = "<ul>"
        for conflict in obj.sync_conflicts:
            html += f"<li>{conflict}</li>"
        html += "</ul>"
        
        return format_html(html)
    conflicts_display.short_description = '충돌 내역'
    
    actions = ['mark_for_sync', 'resolve_conflicts', 'archive_pages']
    
    def mark_for_sync(self, request, queryset):
        """동기화 대상으로 표시"""
        count = queryset.update(is_dirty=True)
        self.message_user(request, f'{count}개 페이지가 동기화 대상으로 표시되었습니다.')
    mark_for_sync.short_description = '동기화 대상으로 표시'
    
    def resolve_conflicts(self, request, queryset):
        """충돌 해결 (로컬 우선)"""
        count = queryset.update(sync_conflicts=[])
        self.message_user(request, f'{count}개 페이지의 충돌이 해결되었습니다.')
    resolve_conflicts.short_description = '충돌 해결'
    
    def archive_pages(self, request, queryset):
        """페이지 보관"""
        count = queryset.update(status=NotionPage.PageStatus.ARCHIVED)
        self.message_user(request, f'{count}개 페이지가 보관되었습니다.')
    archive_pages.short_description = '선택된 페이지 보관'


@admin.register(SyncHistory)
class SyncHistoryAdmin(admin.ModelAdmin):
    """동기화 기록 관리"""
    
    list_display = [
        'database', 'sync_type', 'status', 'success_rate', 'total_pages',
        'pages_created', 'pages_updated', 'started_at', 'duration_display'
    ]
    list_filter = ['sync_type', 'status', 'started_at', 'database']
    search_fields = ['database__title', 'sync_id', 'error_message']
    readonly_fields = [
        'sync_id', 'started_at', 'completed_at', 'duration', 'success_rate',
        'error_details_display'
    ]
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('database', 'sync_type', 'status', 'triggered_by')
        }),
        ('시간 정보', {
            'fields': ('started_at', 'completed_at', 'duration')
        }),
        ('통계', {
            'fields': (
                'total_pages', 'pages_created', 'pages_updated', 
                'pages_deleted', 'pages_failed', 'success_rate'
            )
        }),
        ('오류 정보', {
            'fields': ('error_message', 'error_details_display'),
            'classes': ('collapse',)
        }),
        ('고유 식별자', {
            'fields': ('sync_id',),
            'classes': ('collapse',)
        }),
    )
    
    def duration_display(self, obj):
        """소요 시간 표시"""
        if obj.duration:
            return f"{obj.duration.total_seconds():.1f}초"
        return "-"
    duration_display.short_description = '소요 시간'
    
    def error_details_display(self, obj):
        """오류 세부 정보 표시"""
        if not obj.error_details:
            return "오류 없음"
        
        html = "<ul>"
        for error in obj.error_details:
            page_id = error.get('page_id', 'Unknown')
            error_msg = error.get('error', 'Unknown error')
            timestamp = error.get('timestamp', '')
            html += f"<li><strong>{page_id}</strong>: {error_msg} <small>({timestamp})</small></li>"
        html += "</ul>"
        
        return format_html(html)
    error_details_display.short_description = '오류 세부사항'
    
    def has_delete_permission(self, request, obj=None):
        """삭제 권한 제한 (최근 30일 내 기록만 삭제 가능)"""
        if obj:
            cutoff_date = timezone.now() - timezone.timedelta(days=30)
            return obj.started_at < cutoff_date
        return True


@admin.register(NotionWebhook)
class NotionWebhookAdmin(admin.ModelAdmin):
    """Notion 웹훅 관리"""
    
    list_display = [
        'database', 'webhook_id', 'is_active', 'total_calls', 
        'last_called', 'created_at'
    ]
    list_filter = ['is_active', 'created_at', 'last_called']
    search_fields = ['webhook_id', 'database__title']
    readonly_fields = ['webhook_id', 'total_calls', 'last_called', 'created_at', 'updated_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('database', 'webhook_id', 'is_active')
        }),
        ('이벤트 설정', {
            'fields': ('event_types',)
        }),
        ('통계', {
            'fields': ('total_calls', 'last_called')
        }),
        ('메타데이터', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_webhooks', 'deactivate_webhooks']
    
    def activate_webhooks(self, request, queryset):
        """웹훅 활성화"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count}개 웹훅이 활성화되었습니다.')
    activate_webhooks.short_description = '선택된 웹훅 활성화'
    
    def deactivate_webhooks(self, request, queryset):
        """웹훅 비활성화"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count}개 웹훅이 비활성화되었습니다.')
    deactivate_webhooks.short_description = '선택된 웹훅 비활성화'


# 커스텀 어드민 액션
def export_sync_history_csv(modeladmin, request, queryset):
    """동기화 기록 CSV 내보내기"""
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sync_history.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Database', 'Sync Type', 'Status', 'Started At', 'Duration',
        'Total Pages', 'Created', 'Updated', 'Failed', 'Success Rate'
    ])
    
    for sync in queryset:
        writer.writerow([
            sync.database.title,
            sync.get_sync_type_display(),
            sync.get_status_display(),
            sync.started_at.strftime('%Y-%m-%d %H:%M:%S'),
            sync.duration.total_seconds() if sync.duration else 0,
            sync.total_pages,
            sync.pages_created,
            sync.pages_updated,
            sync.pages_failed,
            f"{sync.success_rate:.1f}%"
        ])
    
    return response

export_sync_history_csv.short_description = "선택된 동기화 기록을 CSV로 내보내기"

# 동기화 기록에 CSV 내보내기 액션 추가
SyncHistoryAdmin.actions = list(SyncHistoryAdmin.actions) + [export_sync_history_csv]