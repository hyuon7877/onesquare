"""
피드백 시스템 Django 관리자 설정
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    FeedbackThread,
    ThreadParticipant,
    FeedbackMessage,
    MediaAttachment,
    FeedbackNotification
)


class ThreadParticipantInline(admin.TabularInline):
    """스레드 참여자 인라인"""
    model = ThreadParticipant
    extra = 0
    readonly_fields = ['joined_at']


class FeedbackMessageInline(admin.StackedInline):
    """피드백 메시지 인라인"""
    model = FeedbackMessage
    extra = 0
    readonly_fields = ['created_at', 'updated_at']
    fields = ['sender', 'message_type', 'content', 'parent_message', 'is_read', 'is_system']


@admin.register(FeedbackThread)
class FeedbackThreadAdmin(admin.ModelAdmin):
    """피드백 스레드 관리"""
    list_display = ['title', 'thread_type', 'status', 'creator', 'participant_count', 'message_count', 'created_at']
    list_filter = ['thread_type', 'status', 'created_at']
    search_fields = ['title', 'creator__username', 'creator__first_name', 'creator__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_activity']
    filter_horizontal = ['participants']
    
    inlines = [ThreadParticipantInline, FeedbackMessageInline]
    
    fieldsets = [
        ('기본 정보', {
            'fields': ['title', 'thread_type', 'status', 'creator']
        }),
        ('Notion 연동', {
            'fields': ['notion_page_id'],
            'classes': ['collapse']
        }),
        ('메타데이터', {
            'fields': ['id', 'created_at', 'updated_at', 'last_activity'],
            'classes': ['collapse']
        })
    ]
    
    def participant_count(self, obj):
        """참여자 수"""
        return obj.participants.count()
    participant_count.short_description = '참여자 수'
    
    def message_count(self, obj):
        """메시지 수"""
        return obj.messages.count()
    message_count.short_description = '메시지 수'


class MediaAttachmentInline(admin.TabularInline):
    """미디어 첨부파일 인라인"""
    model = MediaAttachment
    extra = 0
    readonly_fields = ['created_at', 'file_size', 'media_type']
    fields = ['file', 'original_filename', 'media_type', 'file_size', 'compression_level']


@admin.register(FeedbackMessage)
class FeedbackMessageAdmin(admin.ModelAdmin):
    """피드백 메시지 관리"""
    list_display = ['thread', 'sender', 'message_type', 'content_preview', 'attachment_count', 'is_read', 'created_at']
    list_filter = ['message_type', 'is_read', 'is_system', 'created_at']
    search_fields = ['content', 'sender__username', 'thread__title']
    readonly_fields = ['id', 'created_at', 'updated_at', 'notion_synced']
    
    inlines = [MediaAttachmentInline]
    
    fieldsets = [
        ('메시지 정보', {
            'fields': ['thread', 'sender', 'message_type', 'content']
        }),
        ('회신', {
            'fields': ['parent_message'],
            'classes': ['collapse']
        }),
        ('상태', {
            'fields': ['is_read', 'is_edited', 'is_system']
        }),
        ('Notion 연동', {
            'fields': ['notion_synced'],
            'classes': ['collapse']
        }),
        ('메타데이터', {
            'fields': ['id', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]
    
    def content_preview(self, obj):
        """내용 미리보기"""
        if len(obj.content) > 100:
            return obj.content[:100] + "..."
        return obj.content
    content_preview.short_description = '내용'
    
    def attachment_count(self, obj):
        """첨부파일 수"""
        return obj.attachments.count()
    attachment_count.short_description = '첨부파일 수'


@admin.register(MediaAttachment)
class MediaAttachmentAdmin(admin.ModelAdmin):
    """미디어 첨부파일 관리"""
    list_display = ['original_filename', 'media_type', 'formatted_file_size', 'is_compressed', 'message_thread', 'created_at']
    list_filter = ['media_type', 'is_compressed', 'compression_level', 'created_at']
    search_fields = ['original_filename', 'message__thread__title']
    readonly_fields = ['id', 'file_size', 'formatted_file_size', 'media_type', 'width', 'height', 'created_at']
    
    fieldsets = [
        ('파일 정보', {
            'fields': ['file', 'original_filename', 'media_type', 'file_size', 'formatted_file_size']
        }),
        ('미디어 정보', {
            'fields': ['width', 'height', 'duration'],
            'classes': ['collapse']
        }),
        ('압축 정보', {
            'fields': ['is_compressed', 'compression_level', 'original_size']
        }),
        ('썸네일', {
            'fields': ['thumbnail'],
            'classes': ['collapse']
        }),
        ('메타데이터', {
            'fields': ['id', 'created_at'],
            'classes': ['collapse']
        })
    ]
    
    def message_thread(self, obj):
        """메시지가 속한 스레드"""
        return obj.message.thread.title
    message_thread.short_description = '스레드'
    
    def formatted_file_size(self, obj):
        """포맷된 파일 크기"""
        return obj.formatted_file_size
    formatted_file_size.short_description = '파일 크기'


@admin.register(FeedbackNotification)
class FeedbackNotificationAdmin(admin.ModelAdmin):
    """피드백 알림 관리"""
    list_display = ['title', 'notification_type', 'recipient', 'thread', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['title', 'content', 'recipient__username', 'thread__title']
    readonly_fields = ['id', 'created_at']
    
    fieldsets = [
        ('알림 정보', {
            'fields': ['recipient', 'thread', 'message', 'notification_type']
        }),
        ('내용', {
            'fields': ['title', 'content']
        }),
        ('상태', {
            'fields': ['is_read']
        }),
        ('메타데이터', {
            'fields': ['id', 'created_at'],
            'classes': ['collapse']
        })
    ]


@admin.register(ThreadParticipant)
class ThreadParticipantAdmin(admin.ModelAdmin):
    """스레드 참여자 관리"""
    list_display = ['thread', 'user', 'role', 'is_active', 'joined_at']
    list_filter = ['role', 'is_active', 'joined_at']
    search_fields = ['thread__title', 'user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['joined_at']
    
    fieldsets = [
        ('참여 정보', {
            'fields': ['thread', 'user', 'role', 'is_active']
        }),
        ('메타데이터', {
            'fields': ['joined_at'],
            'classes': ['collapse']
        })
    ]
