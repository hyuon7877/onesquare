"""
멀티미디어 피드백 시스템 모델
파트너-관리자 간 양방향 피드백을 지원하는 스레드형 댓글 시스템
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.utils import timezone
import uuid
import os
from PIL import Image
import io
from django.core.files.base import ContentFile

User = get_user_model()

class FeedbackThread(models.Model):
    """피드백 스레드 - 하나의 피드백 주제"""
    THREAD_TYPES = [
        ('task_feedback', '업무 피드백'),
        ('report_feedback', '보고서 피드백'),
        ('general_feedback', '일반 피드백'),
        ('urgent_feedback', '긴급 피드백'),
    ]
    
    STATUS_CHOICES = [
        ('active', '활성'),
        ('resolved', '해결됨'),
        ('closed', '종료됨'),
        ('archived', '보관됨'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, verbose_name='제목')
    thread_type = models.CharField(max_length=20, choices=THREAD_TYPES, default='general_feedback', verbose_name='피드백 유형')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='상태')
    
    # 참여자
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_feedback_threads', verbose_name='생성자')
    participants = models.ManyToManyField(User, through='ThreadParticipant', related_name='feedback_threads', verbose_name='참여자')
    
    # Notion 연동
    notion_page_id = models.CharField(max_length=100, blank=True, null=True, verbose_name='Notion 페이지 ID')
    
    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    last_activity = models.DateTimeField(auto_now=True, verbose_name='마지막 활동일시')
    
    class Meta:
        verbose_name = '피드백 스레드'
        verbose_name_plural = '피드백 스레드들'
        ordering = ['-last_activity']
    
    def __str__(self):
        return f"{self.title} ({self.get_thread_type_display()})"
    
    @property
    def unread_count(self):
        """읽지 않은 메시지 수"""
        return self.messages.filter(is_read=False).count()
    
    def mark_as_read(self, user):
        """사용자가 스레드를 읽음으로 표시"""
        self.messages.filter(sender__ne=user, is_read=False).update(is_read=True)
    
    def get_latest_message(self):
        """최신 메시지 반환"""
        return self.messages.order_by('-created_at').first()


class ThreadParticipant(models.Model):
    """스레드 참여자 중간 테이블"""
    ROLE_CHOICES = [
        ('admin', '관리자'),
        ('partner', '파트너'),
        ('observer', '참관자'),
    ]
    
    thread = models.ForeignKey(FeedbackThread, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='partner', verbose_name='역할')
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name='참여일시')
    is_active = models.BooleanField(default=True, verbose_name='활성 상태')
    
    class Meta:
        verbose_name = '스레드 참여자'
        verbose_name_plural = '스레드 참여자들'
        unique_together = ['thread', 'user']


class FeedbackMessage(models.Model):
    """피드백 메시지 - 스레드 내의 개별 메시지"""
    MESSAGE_TYPES = [
        ('text', '텍스트'),
        ('image', '이미지'),
        ('video', '비디오'),
        ('file', '파일'),
        ('system', '시스템 메시지'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(FeedbackThread, on_delete=models.CASCADE, related_name='messages', verbose_name='스레드')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_feedback_messages', verbose_name='발신자')
    
    # 메시지 내용
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='text', verbose_name='메시지 유형')
    content = models.TextField(verbose_name='내용')
    
    # 회신 (스레드형 댓글)
    parent_message = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies', verbose_name='부모 메시지')
    
    # 상태
    is_read = models.BooleanField(default=False, verbose_name='읽음 여부')
    is_edited = models.BooleanField(default=False, verbose_name='수정됨')
    is_system = models.BooleanField(default=False, verbose_name='시스템 메시지')
    
    # Notion 연동
    notion_synced = models.BooleanField(default=False, verbose_name='Notion 동기화됨')
    
    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        verbose_name = '피드백 메시지'
        verbose_name_plural = '피드백 메시지들'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"
    
    @property
    def reply_count(self):
        """회신 수"""
        return self.replies.count()
    
    def get_attachments(self):
        """첨부파일 목록"""
        return self.attachments.all()


class MediaAttachment(models.Model):
    """미디어 첨부파일"""
    MEDIA_TYPES = [
        ('image', '이미지'),
        ('video', '비디오'),
        ('document', '문서'),
        ('audio', '오디오'),
        ('other', '기타'),
    ]
    
    COMPRESSION_LEVELS = [
        ('none', '압축 없음'),
        ('low', '낮은 압축'),
        ('medium', '중간 압축'),
        ('high', '높은 압축'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(FeedbackMessage, on_delete=models.CASCADE, related_name='attachments', verbose_name='메시지')
    
    # 파일 정보
    file = models.FileField(upload_to='feedback/media/%Y/%m/', verbose_name='파일')
    original_filename = models.CharField(max_length=255, verbose_name='원본 파일명')
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPES, verbose_name='미디어 유형')
    file_size = models.PositiveIntegerField(verbose_name='파일 크기 (bytes)')
    
    # 이미지/비디오 정보
    width = models.PositiveIntegerField(null=True, blank=True, verbose_name='가로 크기')
    height = models.PositiveIntegerField(null=True, blank=True, verbose_name='세로 크기')
    duration = models.FloatField(null=True, blank=True, verbose_name='재생 시간 (초)')
    
    # 압축 정보
    is_compressed = models.BooleanField(default=False, verbose_name='압축됨')
    compression_level = models.CharField(max_length=20, choices=COMPRESSION_LEVELS, default='none', verbose_name='압축 레벨')
    original_size = models.PositiveIntegerField(null=True, blank=True, verbose_name='원본 파일 크기')
    
    # 썸네일 (이미지/비디오용)
    thumbnail = models.FileField(upload_to='feedback/thumbnails/%Y/%m/', null=True, blank=True, verbose_name='썸네일')
    
    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='업로드일시')
    
    class Meta:
        verbose_name = '미디어 첨부파일'
        verbose_name_plural = '미디어 첨부파일들'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.original_filename} ({self.get_media_type_display()})"
    
    def save(self, *args, **kwargs):
        """파일 저장 시 자동 처리"""
        if self.file:
            # 파일 크기 설정
            self.file_size = self.file.size
            
            # 미디어 유형 자동 감지
            if not self.media_type:
                self.media_type = self._detect_media_type()
            
            # 이미지 처리
            if self.media_type == 'image':
                self._process_image()
        
        super().save(*args, **kwargs)
    
    def _detect_media_type(self):
        """파일 확장자로 미디어 유형 감지"""
        if not self.file:
            return 'other'
        
        ext = os.path.splitext(self.file.name)[1].lower()
        
        image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
        video_exts = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm']
        audio_exts = ['.mp3', '.wav', '.aac', '.ogg', '.flac']
        doc_exts = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt']
        
        if ext in image_exts:
            return 'image'
        elif ext in video_exts:
            return 'video'
        elif ext in audio_exts:
            return 'audio'
        elif ext in doc_exts:
            return 'document'
        else:
            return 'other'
    
    def _process_image(self):
        """이미지 처리 및 압축"""
        if not self.file:
            return
        
        try:
            # PIL로 이미지 열기
            image = Image.open(self.file)
            
            # 크기 정보 저장
            self.width, self.height = image.size
            self.original_size = self.file_size
            
            # 이미지 압축 (설정에 따라)
            if self.compression_level in ['medium', 'high']:
                self._compress_image(image)
            
            # 썸네일 생성
            self._generate_thumbnail(image)
            
        except Exception as e:
            # 이미지 처리 실패 시 로그 남기기
            print(f"이미지 처리 실패: {e}")
    
    def _compress_image(self, image):
        """이미지 압축"""
        # 압축 품질 설정
        quality_map = {
            'low': 95,
            'medium': 80,
            'high': 60,
        }
        quality = quality_map.get(self.compression_level, 95)
        
        # 최대 크기 제한 (큰 이미지 리사이징)
        max_dimension = 1920 if self.compression_level == 'low' else 1280
        if max(image.size) > max_dimension:
            image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
            self.width, self.height = image.size
        
        # 압축된 이미지 저장
        output = io.BytesIO()
        image_format = 'JPEG' if image.format != 'PNG' else 'PNG'
        image.save(output, format=image_format, quality=quality, optimize=True)
        
        # 압축된 파일로 교체
        compressed_file = ContentFile(output.getvalue())
        self.file.save(
            self.file.name,
            compressed_file,
            save=False
        )
        
        self.is_compressed = True
        self.file_size = len(output.getvalue())
        output.close()
    
    def _generate_thumbnail(self, image):
        """썸네일 생성"""
        try:
            # 썸네일 크기 설정
            thumbnail_size = (300, 300)
            
            # 썸네일 생성
            thumbnail_image = image.copy()
            thumbnail_image.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
            
            # 썸네일 저장
            thumb_output = io.BytesIO()
            thumb_format = 'JPEG'
            thumbnail_image.save(thumb_output, format=thumb_format, quality=85, optimize=True)
            
            # 파일명 생성
            base_name = os.path.splitext(self.file.name)[0]
            thumb_name = f"{base_name}_thumb.jpg"
            
            self.thumbnail.save(
                thumb_name,
                ContentFile(thumb_output.getvalue()),
                save=False
            )
            thumb_output.close()
            
        except Exception as e:
            print(f"썸네일 생성 실패: {e}")
    
    @property
    def formatted_file_size(self):
        """사람이 읽기 쉬운 파일 크기"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    @property
    def is_image(self):
        """이미지 여부"""
        return self.media_type == 'image'
    
    @property
    def is_video(self):
        """비디오 여부"""
        return self.media_type == 'video'


class FeedbackNotification(models.Model):
    """피드백 알림"""
    NOTIFICATION_TYPES = [
        ('new_message', '새 메시지'),
        ('thread_created', '스레드 생성됨'),
        ('thread_resolved', '스레드 해결됨'),
        ('mention', '언급됨'),
        ('assignment', '할당됨'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='feedback_notifications', verbose_name='수신자')
    thread = models.ForeignKey(FeedbackThread, on_delete=models.CASCADE, related_name='notifications', verbose_name='스레드')
    message = models.ForeignKey(FeedbackMessage, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications', verbose_name='메시지')
    
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, verbose_name='알림 유형')
    title = models.CharField(max_length=200, verbose_name='제목')
    content = models.TextField(verbose_name='내용')
    
    is_read = models.BooleanField(default=False, verbose_name='읽음 여부')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    
    class Meta:
        verbose_name = '피드백 알림'
        verbose_name_plural = '피드백 알림들'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.recipient.username}: {self.title}"
