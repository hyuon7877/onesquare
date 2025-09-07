"""캘린더 태스크 모델"""
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
import json


class Calendar(models.Model):
    """캘린더 - 사용자별 또는 팀별 캘린더"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_calendars')
    color = models.CharField(max_length=7, default='#007bff')  # HEX 색상 코드
    is_public = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    
    # 공유 설정
    shared_with = models.ManyToManyField(User, related_name='shared_calendars', blank=True)
    share_permission = models.CharField(
        max_length=10,
        choices=[
            ('view', '보기만'),
            ('edit', '편집 가능'),
            ('admin', '관리자')
        ],
        default='view'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default', 'name']
        unique_together = ['owner', 'name']
    
    def __str__(self):
        return f"{self.owner.username}'s {self.name}"
    
    def can_user_edit(self, user):
        """사용자가 편집 권한이 있는지 확인"""
        if user == self.owner:
            return True
        if user in self.shared_with.all():
            return self.share_permission in ['edit', 'admin']
        return False


class Event(models.Model):
    """캘린더 이벤트"""
    PRIORITY_CHOICES = [
        ('low', '낮음'),
        ('medium', '보통'),
        ('high', '높음'),
        ('urgent', '긴급')
    ]
    
    STATUS_CHOICES = [
        ('scheduled', '예정'),
        ('in_progress', '진행중'),
        ('completed', '완료'),
        ('cancelled', '취소'),
        ('postponed', '연기')
    ]
    
    calendar = models.ForeignKey(Calendar, on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    
    # 시간 설정
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    all_day = models.BooleanField(default=False)
    timezone = models.CharField(max_length=50, default='Asia/Seoul')
    
    # 태스크 관련
    is_task = models.BooleanField(default=False)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    progress = models.IntegerField(default=0)  # 0-100 진행률
    
    # 알림 설정
    reminder_minutes = models.IntegerField(null=True, blank=True)  # 몇 분 전 알림
    reminder_sent = models.BooleanField(default=False)
    
    # 참석자
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_events')
    attendees = models.ManyToManyField(User, related_name='attending_events', blank=True)
    
    # 카테고리 및 태그
    category = models.CharField(max_length=50, blank=True)
    tags = models.JSONField(default=list, blank=True)
    color = models.CharField(max_length=7, blank=True)  # 이벤트별 색상 (비어있으면 캘린더 색상 사용)
    
    # 첨부파일 및 링크
    attachments = models.JSONField(default=list, blank=True)
    meeting_link = models.URLField(blank=True)
    
    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['start_date', 'priority']
        indexes = [
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['status', 'is_task']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.start_date.strftime('%Y-%m-%d %H:%M')})"
    
    def clean(self):
        """유효성 검사"""
        if self.end_date < self.start_date:
            raise ValidationError("종료 시간은 시작 시간보다 늦어야 합니다.")
        
        if self.is_task and self.progress < 0 or self.progress > 100:
            raise ValidationError("진행률은 0-100 사이여야 합니다.")
    
    def get_duration(self):
        """이벤트 기간 반환"""
        return self.end_date - self.start_date
    
    def is_overdue(self):
        """기한 초과 여부"""
        if self.is_task and self.status not in ['completed', 'cancelled']:
            return timezone.now() > self.end_date
        return False
    
    def get_color(self):
        """이벤트 색상 반환"""
        return self.color or self.calendar.color


class RecurringEvent(models.Model):
    """반복 이벤트 설정"""
    FREQUENCY_CHOICES = [
        ('daily', '매일'),
        ('weekly', '매주'),
        ('monthly', '매월'),
        ('yearly', '매년'),
        ('custom', '사용자 정의')
    ]
    
    WEEKDAY_CHOICES = [
        (0, '월요일'),
        (1, '화요일'),
        (2, '수요일'),
        (3, '목요일'),
        (4, '금요일'),
        (5, '토요일'),
        (6, '일요일')
    ]
    
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='recurrence')
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES)
    interval = models.IntegerField(default=1)  # 반복 간격 (예: 2주마다)
    
    # 반복 패턴
    weekdays = models.JSONField(default=list, blank=True)  # 주간 반복시 요일 선택 [0,2,4] = 월,수,금
    month_day = models.IntegerField(null=True, blank=True)  # 매월 특정일
    month_week = models.IntegerField(null=True, blank=True)  # 매월 몇째 주 (-1 = 마지막 주)
    
    # 반복 종료
    end_type = models.CharField(
        max_length=10,
        choices=[
            ('never', '종료 없음'),
            ('after', '횟수 지정'),
            ('until', '날짜 지정')
        ],
        default='never'
    )
    occurrences = models.IntegerField(null=True, blank=True)  # 반복 횟수
    end_date = models.DateTimeField(null=True, blank=True)  # 반복 종료일
    
    # 예외 날짜 (특정 날짜 제외)
    exceptions = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.event.title} - {self.get_frequency_display()}"
    
    def generate_occurrences(self, start_date=None, end_date=None):
        """지정된 기간 내의 반복 이벤트 인스턴스 생성"""
        occurrences = []
        current_date = self.event.start_date
        
        if start_date:
            current_date = max(current_date, start_date)
        
        max_date = end_date or (current_date + timedelta(days=365))  # 기본 1년
        
        if self.end_type == 'until' and self.end_date:
            max_date = min(max_date, self.end_date)
        
        count = 0
        while current_date <= max_date:
            # 예외 날짜 확인
            if current_date.date().isoformat() not in self.exceptions:
                occurrences.append(current_date)
                count += 1
                
                # 횟수 제한 확인
                if self.end_type == 'after' and count >= self.occurrences:
                    break
            
            # 다음 반복 날짜 계산
            current_date = self.get_next_occurrence(current_date)
            
            if not current_date:
                break
        
        return occurrences
    
    def get_next_occurrence(self, from_date):
        """다음 반복 날짜 계산"""
        if self.frequency == 'daily':
            return from_date + timedelta(days=self.interval)
        elif self.frequency == 'weekly':
            return from_date + timedelta(weeks=self.interval)
        elif self.frequency == 'monthly':
            # 월간 반복 로직 구현
            next_month = from_date.month + self.interval
            year = from_date.year + (next_month - 1) // 12
            month = ((next_month - 1) % 12) + 1
            try:
                return from_date.replace(year=year, month=month)
            except ValueError:
                # 해당 월에 날짜가 없는 경우 (예: 31일)
                return None
        elif self.frequency == 'yearly':
            return from_date.replace(year=from_date.year + self.interval)
        
        return None


class Task(models.Model):
    """태스크 - 이벤트와 연결된 작업 항목"""
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='task_detail')
    
    # 체크리스트
    checklist = models.JSONField(default=list, blank=True)
    # 예: [{"item": "준비물 확인", "done": true}, {"item": "발표자료 작성", "done": false}]
    
    # 할당
    assigned_to = models.ManyToManyField(User, related_name='assigned_tasks', blank=True)
    
    # 의존성
    depends_on = models.ManyToManyField('self', symmetrical=False, related_name='dependencies', blank=True)
    
    # 예상 소요 시간 (분 단위)
    estimated_minutes = models.IntegerField(null=True, blank=True)
    actual_minutes = models.IntegerField(null=True, blank=True)
    
    # 완료 정보
    completed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='completed_tasks')
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # 노트
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Task: {self.event.title}"
    
    def get_checklist_progress(self):
        """체크리스트 진행률 계산"""
        if not self.checklist:
            return 0
        
        total = len(self.checklist)
        done = sum(1 for item in self.checklist if item.get('done', False))
        
        return int((done / total) * 100) if total > 0 else 0
    
    def update_event_progress(self):
        """체크리스트 기반으로 이벤트 진행률 업데이트"""
        self.event.progress = self.get_checklist_progress()
        self.event.save()


class EventReminder(models.Model):
    """이벤트 알림"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='reminders')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_reminders')
    
    remind_at = models.DateTimeField()
    message = models.TextField()
    
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # 알림 채널
    send_email = models.BooleanField(default=True)
    send_notification = models.BooleanField(default=True)
    send_sms = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['remind_at']
        unique_together = ['event', 'user', 'remind_at']
    
    def __str__(self):
        return f"Reminder for {self.event.title} at {self.remind_at}"


class CalendarShare(models.Model):
    """캘린더 공유 설정"""
    calendar = models.ForeignKey(Calendar, on_delete=models.CASCADE, related_name='shares')
    shared_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='calendar_shares_given')
    shared_with = models.ForeignKey(User, on_delete=models.CASCADE, related_name='calendar_shares_received')
    
    permission = models.CharField(
        max_length=10,
        choices=[
            ('view', '보기만'),
            ('comment', '댓글 가능'),
            ('edit', '편집 가능'),
            ('admin', '관리자')
        ],
        default='view'
    )
    
    # 공유 링크
    share_token = models.CharField(max_length=100, unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['calendar', 'shared_with']
    
    def __str__(self):
        return f"{self.calendar.name} shared with {self.shared_with.username}"
    
    def is_expired(self):
        """공유 만료 여부 확인"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
