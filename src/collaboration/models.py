from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
import re

class Comment(models.Model):
    """실시간 댓글 모델"""
    
    # Generic relation to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # 댓글 정보
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField(verbose_name='내용')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    
    # 멘션 기능
    mentioned_users = models.ManyToManyField(User, related_name='mentioned_in_comments', blank=True)
    
    # 상태 정보
    is_edited = models.BooleanField(default=False, verbose_name='수정됨')
    is_deleted = models.BooleanField(default=False, verbose_name='삭제됨')
    
    # 시간 정보
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = '댓글'
        verbose_name_plural = '댓글'
    
    def __str__(self):
        return f"{self.author.username}: {self.content[:50]}"
    
    def save(self, *args, **kwargs):
        # 멘션 추출 (@username)
        if self.content:
            mentions = re.findall(r'@(\w+)', self.content)
            super().save(*args, **kwargs)
            
            if mentions:
                mentioned_users = User.objects.filter(username__in=mentions)
                self.mentioned_users.set(mentioned_users)
        else:
            super().save(*args, **kwargs)
    
    def get_replies(self):
        """답글 가져오기"""
        return self.replies.filter(is_deleted=False)
    
    def get_mentioned_usernames(self):
        """멘션된 사용자명 리스트"""
        return list(self.mentioned_users.values_list('username', flat=True))


class Activity(models.Model):
    """활동 피드 모델"""
    
    ACTIVITY_TYPES = [
        ('comment_added', '댓글 작성'),
        ('comment_edited', '댓글 수정'),
        ('comment_deleted', '댓글 삭제'),
        ('mention', '멘션'),
        ('report_created', '리포트 작성'),
        ('report_submitted', '리포트 제출'),
        ('report_approved', '리포트 승인'),
        ('report_rejected', '리포트 반려'),
        ('user_joined', '사용자 가입'),
        ('task_assigned', '작업 할당'),
        ('task_completed', '작업 완료'),
    ]
    
    # 활동 주체
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    
    # 활동 유형
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    
    # 활동 대상 (Generic relation)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # 추가 정보
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # 관련 사용자들 (멘션, 할당 등)
    related_users = models.ManyToManyField(User, related_name='related_activities', blank=True)
    
    # 시간 정보
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['activity_type', 'created_at']),
        ]
        verbose_name = '활동'
        verbose_name_plural = '활동'
    
    def __str__(self):
        return f"{self.user.username} - {self.get_activity_type_display()}"
    
    def get_icon(self):
        """활동 유형별 아이콘"""
        icons = {
            'comment_added': '💬',
            'comment_edited': '✏️',
            'comment_deleted': '🗑️',
            'mention': '@',
            'report_created': '📝',
            'report_submitted': '📤',
            'report_approved': '✅',
            'report_rejected': '❌',
            'user_joined': '👤',
            'task_assigned': '📌',
            'task_completed': '✔️',
        }
        return icons.get(self.activity_type, '📌')
    
    def get_message(self):
        """활동 메시지 생성"""
        messages = {
            'comment_added': f"{self.user.get_full_name() or self.user.username}님이 댓글을 작성했습니다",
            'comment_edited': f"{self.user.get_full_name() or self.user.username}님이 댓글을 수정했습니다",
            'comment_deleted': f"{self.user.get_full_name() or self.user.username}님이 댓글을 삭제했습니다",
            'mention': f"{self.user.get_full_name() or self.user.username}님이 멘션했습니다",
            'report_created': f"{self.user.get_full_name() or self.user.username}님이 리포트를 작성했습니다",
            'report_submitted': f"{self.user.get_full_name() or self.user.username}님이 리포트를 제출했습니다",
            'report_approved': f"{self.user.get_full_name() or self.user.username}님이 리포트를 승인했습니다",
            'report_rejected': f"{self.user.get_full_name() or self.user.username}님이 리포트를 반려했습니다",
            'user_joined': f"{self.user.get_full_name() or self.user.username}님이 가입했습니다",
            'task_assigned': f"{self.user.get_full_name() or self.user.username}님이 작업을 할당했습니다",
            'task_completed': f"{self.user.get_full_name() or self.user.username}님이 작업을 완료했습니다",
        }
        return messages.get(self.activity_type, self.description)


class Notification(models.Model):
    """실시간 알림 모델"""
    
    NOTIFICATION_TYPES = [
        ('comment', '댓글'),
        ('mention', '멘션'),
        ('reply', '답글'),
        ('approval', '승인'),
        ('rejection', '반려'),
        ('assignment', '할당'),
        ('system', '시스템'),
    ]
    
    # 수신자
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    
    # 발신자 (시스템 알림의 경우 null)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications', null=True, blank=True)
    
    # 알림 유형
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    
    # 알림 내용
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # 관련 객체 (Generic relation)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # 상태
    is_read = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)  # 푸시 알림 전송 여부
    
    # 추가 데이터
    action_url = models.URLField(blank=True, help_text='클릭 시 이동할 URL')
    metadata = models.JSONField(default=dict, blank=True)
    
    # 시간 정보
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', 'created_at']),
        ]
        verbose_name = '알림'
        verbose_name_plural = '알림'
    
    def __str__(self):
        return f"{self.recipient.username} - {self.title}"
    
    def mark_as_read(self):
        """알림을 읽음으로 표시"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
    
    def get_icon(self):
        """알림 유형별 아이콘"""
        icons = {
            'comment': '💬',
            'mention': '@',
            'reply': '↩️',
            'approval': '✅',
            'rejection': '❌',
            'assignment': '📌',
            'system': '🔔',
        }
        return icons.get(self.notification_type, '🔔')


class Presence(models.Model):
    """사용자 실시간 상태 모델"""
    
    STATUS_CHOICES = [
        ('online', '온라인'),
        ('away', '자리비움'),
        ('busy', '바쁨'),
        ('offline', '오프라인'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='presence')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offline')
    last_seen = models.DateTimeField(auto_now=True)
    
    # 현재 보고 있는 페이지/객체
    current_page = models.CharField(max_length=200, blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    current_object = GenericForeignKey('content_type', 'object_id')
    
    # 추가 상태 정보
    is_typing = models.BooleanField(default=False)
    typing_in = models.CharField(max_length=100, blank=True)  # 어디에 입력 중인지
    
    class Meta:
        verbose_name = '사용자 상태'
        verbose_name_plural = '사용자 상태'
    
    def __str__(self):
        return f"{self.user.username} - {self.get_status_display()}"
    
    def update_activity(self):
        """활동 시간 업데이트"""
        self.last_seen = timezone.now()
        if self.status == 'offline':
            self.status = 'online'
        self.save()
    
    def set_typing(self, is_typing=True, location=''):
        """타이핑 상태 설정"""
        self.is_typing = is_typing
        self.typing_in = location
        self.save()