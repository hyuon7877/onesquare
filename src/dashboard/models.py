from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# 중복 모델 제거: Activity와 Notification은 collaboration.models 사용
# dashboard 앱은 DashboardStatistics와 ChartData만 유지


class DashboardStatistics(models.Model):
    """대시보드 통계 모델"""
    date = models.DateField(default=timezone.now)
    total_users = models.IntegerField(default=0)
    active_projects = models.IntegerField(default=0)
    completed_tasks = models.IntegerField(default=0)
    pending_reports = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        verbose_name = '대시보드 통계'
        verbose_name_plural = '대시보드 통계'

    def __str__(self):
        return f"{self.date} 통계"


# Activity와 Notification 모델은 collaboration.models로 이동됨
# 중복을 피하기 위해 주석 처리

# class Activity(models.Model):
#     """활동 로그 모델 - collaboration.models.Activity 사용"""
#     pass

# class Notification(models.Model):
#     """알림 모델 - collaboration.models.Notification 사용"""
#     pass


class ChartData(models.Model):
    """차트 데이터 모델"""
    CHART_TYPES = [
        ('line', '라인 차트'),
        ('pie', '파이 차트'),
        ('bar', '바 차트'),
    ]

    chart_type = models.CharField(max_length=10, choices=CHART_TYPES)
    data = models.JSONField()
    date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = '차트 데이터'
        verbose_name_plural = '차트 데이터'

    def __str__(self):
        return f"{self.get_chart_type_display()} - {self.date}"


class CalendarEvent(models.Model):
    """캘린더 이벤트 모델"""
    EVENT_TYPES = [
        ('meeting', '회의'),
        ('task', '작업'),
        ('deadline', '마감일'),
        ('reminder', '알림'),
        ('holiday', '휴일'),
        ('other', '기타'),
    ]
    
    REPEAT_CHOICES = [
        ('none', '반복 없음'),
        ('daily', '매일'),
        ('weekly', '매주'),
        ('monthly', '매월'),
        ('yearly', '매년'),
    ]
    
    title = models.CharField(max_length=200, verbose_name='제목')
    description = models.TextField(blank=True, verbose_name='설명')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, default='meeting', verbose_name='이벤트 유형')
    
    # 시간 정보
    start_date = models.DateTimeField(verbose_name='시작 일시')
    end_date = models.DateTimeField(verbose_name='종료 일시')
    all_day = models.BooleanField(default=False, verbose_name='종일 이벤트')
    
    # 반복 설정
    repeat = models.CharField(max_length=20, choices=REPEAT_CHOICES, default='none', verbose_name='반복')
    repeat_until = models.DateField(null=True, blank=True, verbose_name='반복 종료일')
    
    # 참석자 및 위치
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_events', verbose_name='주최자')
    participants = models.ManyToManyField(User, related_name='participating_events', blank=True, verbose_name='참석자')
    location = models.CharField(max_length=200, blank=True, verbose_name='위치')
    
    # 알림 설정
    reminder_minutes = models.IntegerField(default=15, verbose_name='알림 시간(분)')
    
    # 색상 및 표시
    color = models.CharField(max_length=7, default='#0d6efd', verbose_name='색상')
    is_public = models.BooleanField(default=True, verbose_name='공개 여부')
    
    # 메타 정보
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['start_date']
        verbose_name = '캘린더 이벤트'
        verbose_name_plural = '캘린더 이벤트'
        indexes = [
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['organizer', 'start_date']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.start_date.strftime('%Y-%m-%d %H:%M')}"
    
    def get_duration(self):
        """이벤트 지속 시간 계산"""
        return self.end_date - self.start_date
    
    def is_ongoing(self):
        """현재 진행 중인 이벤트인지 확인"""
        now = timezone.now()
        return self.start_date <= now <= self.end_date