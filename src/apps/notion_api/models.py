"""
OneSquare Notion API 연동 - 데이터 모델

이 모듈은 Notion과의 데이터 동기화를 위한 Django 모델들을 정의합니다.
- NotionDatabase: Notion 데이터베이스 메타데이터
- NotionPage: Notion 페이지 캐시
- SyncHistory: 동기화 기록
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
import json
import uuid

User = get_user_model()


class NotionDatabase(models.Model):
    """
    Notion 데이터베이스 메타데이터
    각 Notion 데이터베이스의 설정과 스키마 정보를 저장
    """
    
    class DatabaseType(models.TextChoices):
        PROJECTS = 'projects', '프로젝트'
        TASKS = 'tasks', '작업'
        TEAM_MEMBERS = 'team_members', '팀원'
        PARTNERS = 'partners', '파트너'
        REPORTS = 'reports', '리포트'
        CALENDAR = 'calendar', '캘린더'
        CUSTOM = 'custom', '커스텀'
    
    # Notion 데이터베이스 정보
    notion_id = models.CharField(
        max_length=36, 
        unique=True, 
        help_text="Notion 데이터베이스 ID"
    )
    title = models.CharField(max_length=255, help_text="데이터베이스 제목")
    description = models.TextField(blank=True, help_text="데이터베이스 설명")
    
    # 메타데이터
    database_type = models.CharField(
        max_length=20, 
        choices=DatabaseType.choices, 
        default=DatabaseType.CUSTOM,
        help_text="데이터베이스 유형"
    )
    
    # 스키마 정보 (JSON으로 저장)
    schema = models.JSONField(
        default=dict,
        help_text="Notion 데이터베이스 스키마 (속성 정의)"
    )
    
    # 동기화 설정
    is_active = models.BooleanField(default=True, help_text="동기화 활성화 여부")
    sync_interval = models.IntegerField(
        default=300, 
        help_text="동기화 간격 (초)"
    )
    last_synced = models.DateTimeField(
        null=True, blank=True, 
        help_text="마지막 동기화 시간"
    )
    
    # Django 관리 정보
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        help_text="등록한 사용자"
    )
    
    class Meta:
        verbose_name = "Notion 데이터베이스"
        verbose_name_plural = "Notion 데이터베이스 목록"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.get_database_type_display()})"
    
    def clean(self):
        """모델 유효성 검사"""
        if self.sync_interval < 60:
            raise ValidationError("동기화 간격은 최소 60초 이상이어야 합니다.")
    
    @property
    def is_synced_recently(self):
        """최근 동기화 여부"""
        if not self.last_synced:
            return False
        
        time_diff = timezone.now() - self.last_synced
        return time_diff.total_seconds() < self.sync_interval * 2
    
    def get_property_config(self, property_name):
        """특정 속성의 설정 반환"""
        return self.schema.get('properties', {}).get(property_name, {})
    
    def update_schema(self, new_schema):
        """스키마 업데이트"""
        self.schema = new_schema
        self.updated_at = timezone.now()
        self.save(update_fields=['schema', 'updated_at'])


class NotionPage(models.Model):
    """
    Notion 페이지 캐시
    Notion 페이지 데이터를 로컬에 캐시하여 오프라인 지원 및 성능 향상
    """
    
    class PageStatus(models.TextChoices):
        ACTIVE = 'active', '활성'
        ARCHIVED = 'archived', '보관됨'
        DELETED = 'deleted', '삭제됨'
        DRAFT = 'draft', '초안'
    
    # Notion 페이지 정보
    notion_id = models.CharField(
        max_length=36, 
        unique=True, 
        help_text="Notion 페이지 ID"
    )
    database = models.ForeignKey(
        NotionDatabase, 
        on_delete=models.CASCADE,
        related_name='pages',
        help_text="소속 데이터베이스"
    )
    
    # 페이지 메타데이터
    title = models.CharField(max_length=500, help_text="페이지 제목")
    status = models.CharField(
        max_length=20, 
        choices=PageStatus.choices, 
        default=PageStatus.ACTIVE
    )
    
    # 페이지 내용 (JSON으로 저장)
    properties = models.JSONField(
        default=dict,
        help_text="페이지 속성 데이터"
    )
    content_blocks = models.JSONField(
        default=list,
        help_text="페이지 내용 블록"
    )
    
    # Notion 메타데이터
    notion_created_time = models.DateTimeField(
        help_text="Notion에서의 생성 시간"
    )
    notion_last_edited_time = models.DateTimeField(
        help_text="Notion에서의 마지막 수정 시간"
    )
    notion_created_by = models.CharField(
        max_length=36, 
        default='',
        help_text="Notion 생성자 ID"
    )
    notion_last_edited_by = models.CharField(
        max_length=36, 
        default='',
        help_text="Notion 마지막 수정자 ID"
    )
    
    # 동기화 정보
    local_hash = models.CharField(
        max_length=64, 
        default='',
        help_text="로컬 데이터 해시"
    )
    is_dirty = models.BooleanField(
        default=False, 
        help_text="로컬에서 수정됨 (동기화 필요)"
    )
    sync_conflicts = models.JSONField(
        default=list,
        help_text="동기화 충돌 정보"
    )
    
    # Django 관리 정보
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Notion 페이지"
        verbose_name_plural = "Notion 페이지 목록"
        ordering = ['-notion_last_edited_time']
        indexes = [
            models.Index(fields=['database', 'status']),
            models.Index(fields=['is_dirty']),
            models.Index(fields=['notion_last_edited_time']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.database.title})"
    
    def get_property(self, property_name, default=None):
        """특정 속성값 반환"""
        return self.properties.get(property_name, default)
    
    def set_property(self, property_name, value):
        """속성값 설정 및 dirty 플래그 설정"""
        if self.properties.get(property_name) != value:
            self.properties[property_name] = value
            self.is_dirty = True
            self.updated_at = timezone.now()
    
    def calculate_hash(self):
        """현재 데이터의 해시값 계산"""
        import hashlib
        
        data_str = json.dumps(
            {
                'properties': self.properties,
                'content_blocks': self.content_blocks
            },
            sort_keys=True
        )
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def mark_synced(self):
        """동기화 완료 표시"""
        self.is_dirty = False
        self.local_hash = self.calculate_hash()
        self.sync_conflicts = []
        self.save(update_fields=['is_dirty', 'local_hash', 'sync_conflicts'])


class SyncHistory(models.Model):
    """
    동기화 기록
    Notion과의 데이터 동기화 과정과 결과를 기록
    """
    
    class SyncType(models.TextChoices):
        FULL_SYNC = 'full_sync', '전체 동기화'
        INCREMENTAL = 'incremental', '증분 동기화'
        MANUAL = 'manual', '수동 동기화'
        REAL_TIME = 'real_time', '실시간 동기화'
    
    class SyncStatus(models.TextChoices):
        STARTED = 'started', '시작됨'
        IN_PROGRESS = 'in_progress', '진행 중'
        COMPLETED = 'completed', '완료'
        FAILED = 'failed', '실패'
        PARTIAL = 'partial', '부분 완료'
    
    # 동기화 세션 정보
    sync_id = models.UUIDField(
        default=uuid.uuid4, 
        unique=True,
        help_text="동기화 세션 ID"
    )
    database = models.ForeignKey(
        NotionDatabase, 
        on_delete=models.CASCADE,
        related_name='sync_history',
        help_text="동기화 대상 데이터베이스"
    )
    
    # 동기화 설정
    sync_type = models.CharField(
        max_length=20, 
        choices=SyncType.choices,
        help_text="동기화 유형"
    )
    status = models.CharField(
        max_length=20, 
        choices=SyncStatus.choices,
        default=SyncStatus.STARTED,
        help_text="동기화 상태"
    )
    
    # 시간 정보
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    
    # 동기화 통계
    total_pages = models.IntegerField(default=0, help_text="전체 페이지 수")
    pages_created = models.IntegerField(default=0, help_text="생성된 페이지 수")
    pages_updated = models.IntegerField(default=0, help_text="업데이트된 페이지 수")
    pages_deleted = models.IntegerField(default=0, help_text="삭제된 페이지 수")
    pages_failed = models.IntegerField(default=0, help_text="실패한 페이지 수")
    
    # 오류 정보
    error_message = models.TextField(blank=True, default='', help_text="오류 메시지")
    error_details = models.JSONField(
        default=list,
        help_text="상세 오류 정보"
    )
    
    # 실행 사용자
    triggered_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        help_text="동기화를 실행한 사용자"
    )
    
    class Meta:
        verbose_name = "동기화 기록"
        verbose_name_plural = "동기화 기록 목록"
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['database', 'status']),
            models.Index(fields=['started_at']),
        ]
    
    def __str__(self):
        return f"{self.database.title} - {self.get_sync_type_display()} ({self.status})"
    
    def mark_completed(self):
        """동기화 완료 처리"""
        self.status = self.SyncStatus.COMPLETED
        self.completed_at = timezone.now()
        self.duration = self.completed_at - self.started_at
        self.save(update_fields=['status', 'completed_at', 'duration'])
    
    def mark_failed(self, error_message):
        """동기화 실패 처리"""
        self.status = self.SyncStatus.FAILED
        self.completed_at = timezone.now()
        self.duration = self.completed_at - self.started_at
        self.error_message = error_message
        self.save(update_fields=['status', 'completed_at', 'duration', 'error_message'])
    
    def add_error(self, page_id, error_message):
        """개별 페이지 오류 추가"""
        self.error_details.append({
            'page_id': page_id,
            'error': error_message,
            'timestamp': timezone.now().isoformat()
        })
        self.pages_failed += 1
        self.save(update_fields=['error_details', 'pages_failed'])
    
    @property
    def success_rate(self):
        """성공률 계산"""
        if self.total_pages == 0:
            return 100.0
        
        successful_pages = self.pages_created + self.pages_updated
        return (successful_pages / self.total_pages) * 100


class NotionWebhook(models.Model):
    """
    Notion 웹훅 설정
    실시간 데이터 동기화를 위한 웹훅 관리 (향후 Notion 지원 시)
    """
    
    # 웹훅 정보
    webhook_id = models.CharField(
        max_length=100, 
        unique=True,
        help_text="웹훅 ID"
    )
    database = models.ForeignKey(
        NotionDatabase, 
        on_delete=models.CASCADE,
        related_name='webhooks',
        help_text="연결된 데이터베이스"
    )
    
    # 설정
    event_types = models.JSONField(
        default=list,
        help_text="구독할 이벤트 타입"
    )
    is_active = models.BooleanField(default=True)
    
    # 통계
    total_calls = models.IntegerField(default=0, help_text="총 호출 수")
    last_called = models.DateTimeField(null=True, blank=True)
    
    # Django 관리
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Notion 웹훅"
        verbose_name_plural = "Notion 웹훅 목록"
    
    def __str__(self):
        return f"Webhook for {self.database.title}"