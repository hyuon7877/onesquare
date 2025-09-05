"""
OneSquare 통합 캘린더 시스템 - Django 모델
FullCalendar 기반 일정 관리 및 Notion 연동
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.auth_system.models import CustomUser
import json

User = get_user_model()


class CalendarCategory(models.Model):
    """캘린더 카테고리"""
    
    name = models.CharField(max_length=50, verbose_name='카테고리명')
    color = models.CharField(max_length=7, default='#3788d8', verbose_name='색상', help_text='HEX 색상 코드')
    description = models.TextField(blank=True, verbose_name='설명')
    is_active = models.BooleanField(default=True, verbose_name='활성화')
    
    # 권한 관련
    accessible_user_types = models.JSONField(
        default=list,
        verbose_name='접근 가능한 사용자 타입',
        help_text='["SUPER_ADMIN", "MANAGER"] 형태로 저장'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        verbose_name = '캘린더 카테고리'
        verbose_name_plural = '캘린더 카테고리들'
        db_table = 'calendar_category'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def can_access(self, user):
        """사용자의 카테고리 접근 권한 확인"""
        if not self.accessible_user_types:
            return True  # 제한 없음
        return user.user_type in self.accessible_user_types


class CalendarEvent(models.Model):
    """캘린더 이벤트"""
    
    class EventType(models.TextChoices):
        MEETING = 'meeting', '회의'
        DEADLINE = 'deadline', '마감일'
        VACATION = 'vacation', '휴가'
        WORK = 'work', '업무'
        PERSONAL = 'personal', '개인'
        COMPANY = 'company', '회사'
    
    class Priority(models.TextChoices):
        LOW = 'low', '낮음'
        MEDIUM = 'medium', '보통'
        HIGH = 'high', '높음'
        URGENT = 'urgent', '긴급'
    
    class RecurrenceType(models.TextChoices):
        NONE = 'none', '반복 없음'
        DAILY = 'daily', '매일'
        WEEKLY = 'weekly', '매주'
        MONTHLY = 'monthly', '매월'
        YEARLY = 'yearly', '매년'
    
    title = models.CharField(max_length=200, verbose_name='제목')
    description = models.TextField(blank=True, verbose_name='설명')
    
    # 사용자 및 카테고리
    creator = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='created_events',
        verbose_name='작성자'
    )
    category = models.ForeignKey(
        CalendarCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='카테고리'
    )
    
    # 일정 시간
    start_datetime = models.DateTimeField(verbose_name='시작일시')
    end_datetime = models.DateTimeField(verbose_name='종료일시')
    is_all_day = models.BooleanField(default=False, verbose_name='종일 일정')
    
    # 이벤트 속성
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices,
        default=EventType.WORK,
        verbose_name='이벤트 타입'
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name='우선순위'
    )
    
    # 반복 설정
    recurrence_type = models.CharField(
        max_length=10,
        choices=RecurrenceType.choices,
        default=RecurrenceType.NONE,
        verbose_name='반복 타입'
    )
    recurrence_end_date = models.DateField(null=True, blank=True, verbose_name='반복 종료일')
    
    # 참석자
    attendees = models.ManyToManyField(
        CustomUser,
        through='EventAttendee',
        related_name='attending_events',
        verbose_name='참석자',
        blank=True
    )
    
    # 위치 및 추가 정보
    location = models.CharField(max_length=200, blank=True, verbose_name='장소')
    url = models.URLField(blank=True, verbose_name='관련 URL')
    
    # 알림 설정
    reminder_minutes = models.IntegerField(
        default=15,
        verbose_name='알림 시간(분 전)',
        help_text='이벤트 시작 몇 분 전에 알림을 받을지'
    )
    
    # Notion 연동
    notion_page_id = models.CharField(max_length=100, blank=True, verbose_name='Notion 페이지 ID')
    notion_database_id = models.CharField(max_length=100, blank=True, verbose_name='Notion 데이터베이스 ID')
    last_synced_at = models.DateTimeField(null=True, blank=True, verbose_name='마지막 동기화')
    
    # 시스템 필드
    is_active = models.BooleanField(default=True, verbose_name='활성화')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        verbose_name = '캘린더 이벤트'
        verbose_name_plural = '캘린더 이벤트들'
        db_table = 'calendar_event'
        ordering = ['start_datetime']
        indexes = [
            models.Index(fields=['start_datetime', 'end_datetime']),
            models.Index(fields=['creator', 'is_active']),
            models.Index(fields=['category', 'event_type']),
            models.Index(fields=['notion_page_id']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.start_datetime.strftime('%Y-%m-%d %H:%M')})"
    
    def clean(self):
        """모델 검증"""
        if self.end_datetime <= self.start_datetime:
            raise ValidationError('종료일시는 시작일시보다 늦어야 합니다.')
        
        if self.recurrence_type != self.RecurrenceType.NONE and not self.recurrence_end_date:
            raise ValidationError('반복 일정은 종료일을 설정해야 합니다.')
    
    @property
    def duration_minutes(self):
        """이벤트 지속 시간 (분)"""
        return int((self.end_datetime - self.start_datetime).total_seconds() / 60)
    
    @property
    def is_past(self):
        """과거 이벤트인지 확인"""
        return self.end_datetime < timezone.now()
    
    @property
    def is_today(self):
        """오늘 이벤트인지 확인"""
        today = timezone.now().date()
        return self.start_datetime.date() <= today <= self.end_datetime.date()
    
    @property
    def fullcalendar_format(self):
        """FullCalendar 형식으로 데이터 변환"""
        return {
            'id': str(self.id),
            'title': self.title,
            'start': self.start_datetime.isoformat(),
            'end': self.end_datetime.isoformat(),
            'allDay': self.is_all_day,
            'backgroundColor': self.category.color if self.category else '#3788d8',
            'borderColor': self.category.color if self.category else '#3788d8',
            'textColor': '#ffffff',
            'extendedProps': {
                'description': self.description,
                'eventType': self.event_type,
                'priority': self.priority,
                'location': self.location,
                'creator': self.creator.username,
                'categoryName': self.category.name if self.category else '',
                'attendeeCount': self.attendees.count(),
            }
        }
    
    def can_edit(self, user):
        """사용자의 이벤트 편집 권한 확인"""
        # 작성자는 항상 편집 가능
        if self.creator == user:
            return True
        
        # 관리자 권한 확인
        if user.user_type in ['SUPER_ADMIN', 'MANAGER']:
            return True
        
        # 참석자도 부분적 편집 가능 (구체적인 권한은 뷰에서 처리)
        return self.attendees.filter(id=user.id).exists()
    
    def can_view(self, user):
        """사용자의 이벤트 조회 권한 확인"""
        # 작성자는 항상 조회 가능
        if self.creator == user:
            return True
        
        # 참석자는 조회 가능
        if self.attendees.filter(id=user.id).exists():
            return True
        
        # 카테고리 접근 권한 확인
        if self.category and not self.category.can_access(user):
            return False
        
        # 기본적으로 같은 회사 내에서는 조회 가능 (파트너/도급사 제외)
        if user.user_type in ['SUPER_ADMIN', 'MANAGER', 'TEAM_MEMBER']:
            return True
        
        return False


class EventAttendee(models.Model):
    """이벤트 참석자"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', '대기 중'
        ACCEPTED = 'accepted', '참석'
        DECLINED = 'declined', '불참'
        TENTATIVE = 'tentative', '미정'
    
    event = models.ForeignKey(CalendarEvent, on_delete=models.CASCADE, verbose_name='이벤트')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name='참석자')
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='참석 상태'
    )
    response_at = models.DateTimeField(null=True, blank=True, verbose_name='응답일시')
    notes = models.TextField(blank=True, verbose_name='메모')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        verbose_name = '이벤트 참석자'
        verbose_name_plural = '이벤트 참석자들'
        db_table = 'calendar_event_attendee'
        unique_together = ['event', 'user']
    
    def __str__(self):
        return f"{self.event.title} - {self.user.username} ({self.get_status_display()})"


class EventReminder(models.Model):
    """이벤트 알림"""
    
    class Status(models.TextChoices):
        PENDING = 'pending', '대기 중'
        SENT = 'sent', '발송됨'
        FAILED = 'failed', '실패'
    
    event = models.ForeignKey(
        CalendarEvent, 
        on_delete=models.CASCADE, 
        related_name='reminders',
        verbose_name='이벤트'
    )
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name='사용자')
    
    reminder_datetime = models.DateTimeField(verbose_name='알림 시간')
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='상태'
    )
    
    # 알림 방법 (추후 확장 가능)
    notification_method = models.CharField(
        max_length=20,
        default='push',
        verbose_name='알림 방법',
        help_text='push, email, sms 등'
    )
    
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='발송일시')
    error_message = models.TextField(blank=True, verbose_name='오류 메시지')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    
    class Meta:
        verbose_name = '이벤트 알림'
        verbose_name_plural = '이벤트 알림들'
        db_table = 'calendar_event_reminder'
        unique_together = ['event', 'user', 'reminder_datetime']
    
    def __str__(self):
        return f"{self.event.title} - {self.user.username} 알림"


class CalendarSettings(models.Model):
    """사용자별 캘린더 설정"""
    
    class View(models.TextChoices):
        MONTH = 'dayGridMonth', '월'
        WEEK = 'timeGridWeek', '주'
        DAY = 'timeGridDay', '일'
        LIST = 'listWeek', '목록'
    
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='calendar_settings',
        verbose_name='사용자'
    )
    
    # 기본 뷰 설정
    default_view = models.CharField(
        max_length=20,
        choices=View.choices,
        default=View.MONTH,
        verbose_name='기본 보기'
    )
    
    # 시간 설정
    work_start_time = models.TimeField(default='09:00', verbose_name='업무 시작 시간')
    work_end_time = models.TimeField(default='18:00', verbose_name='업무 종료 시간')
    
    # 알림 설정
    default_reminder_minutes = models.IntegerField(default=15, verbose_name='기본 알림 시간(분)')
    email_notifications = models.BooleanField(default=True, verbose_name='이메일 알림')
    push_notifications = models.BooleanField(default=True, verbose_name='푸시 알림')
    
    # 표시 설정
    show_weekends = models.BooleanField(default=True, verbose_name='주말 표시')
    show_declined_events = models.BooleanField(default=False, verbose_name='거절한 일정 표시')
    
    # 카테고리 필터 (JSON 형태로 저장)
    visible_categories = models.JSONField(
        default=list,
        verbose_name='표시할 카테고리',
        help_text='카테고리 ID 배열'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        verbose_name = '캘린더 설정'
        verbose_name_plural = '캘린더 설정들'
        db_table = 'calendar_settings'
    
    def __str__(self):
        return f"{self.user.username}의 캘린더 설정"


class NotionCalendarSync(models.Model):
    """Notion 캘린더 동기화 로그"""
    
    class SyncType(models.TextChoices):
        CREATE = 'create', '생성'
        UPDATE = 'update', '수정'
        DELETE = 'delete', '삭제'
        SYNC = 'sync', '동기화'
    
    class Status(models.TextChoices):
        PENDING = 'pending', '대기 중'
        SUCCESS = 'success', '성공'
        FAILED = 'failed', '실패'
    
    event = models.ForeignKey(
        CalendarEvent,
        on_delete=models.CASCADE,
        related_name='sync_logs',
        verbose_name='이벤트'
    )
    
    sync_type = models.CharField(
        max_length=10,
        choices=SyncType.choices,
        verbose_name='동기화 타입'
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='상태'
    )
    
    notion_page_id = models.CharField(max_length=100, blank=True, verbose_name='Notion 페이지 ID')
    
    # 요청/응답 데이터
    request_data = models.JSONField(null=True, blank=True, verbose_name='요청 데이터')
    response_data = models.JSONField(null=True, blank=True, verbose_name='응답 데이터')
    error_message = models.TextField(blank=True, verbose_name='오류 메시지')
    
    # 실행 정보
    executed_at = models.DateTimeField(auto_now_add=True, verbose_name='실행일시')
    execution_time_ms = models.IntegerField(null=True, blank=True, verbose_name='실행 시간(ms)')
    
    class Meta:
        verbose_name = 'Notion 동기화 로그'
        verbose_name_plural = 'Notion 동기화 로그들'
        db_table = 'calendar_notion_sync'
        ordering = ['-executed_at']
    
    def __str__(self):
        return f"{self.event.title} - {self.get_sync_type_display()} ({self.get_status_display()})"