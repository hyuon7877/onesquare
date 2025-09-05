"""
OneSquare 통합 관리 대시보드 시스템 - Django 모델
실시간 데이터 시각화 및 권한별 접근 제어
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import json
import uuid
from datetime import datetime, timedelta

User = get_user_model()


class DashboardWidget(models.Model):
    """대시보드 위젯 정의"""
    
    WIDGET_TYPE_CHOICES = [
        ('chart_pie', '원형 차트'),
        ('chart_bar', '막대 차트'),
        ('chart_line', '선형 차트'),
        ('chart_donut', '도넛 차트'),
        ('stats_card', '통계 카드'),
        ('table', '데이터 테이블'),
        ('calendar', '캘린더 위젯'),
        ('notification', '알림 위젯'),
        ('progress', '진행률 위젯'),
        ('map', '지도 위젯'),
        ('list', '목록 위젯'),
        ('custom', '커스텀 위젯'),
    ]
    
    DATA_SOURCE_CHOICES = [
        ('revenue', '매출 데이터'),
        ('calendar', '캘린더 데이터'),
        ('partner_report', '파트너 리포트'),
        ('user_activity', '사용자 활동'),
        ('system_status', '시스템 상태'),
        ('notion_sync', 'Notion 동기화'),
        ('custom_api', '커스텀 API'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name='위젯명')
    title = models.CharField(max_length=200, verbose_name='표시 제목')
    description = models.TextField(blank=True, verbose_name='설명')
    
    # 위젯 타입 및 데이터 소스
    widget_type = models.CharField(max_length=20, choices=WIDGET_TYPE_CHOICES, verbose_name='위젯 타입')
    data_source = models.CharField(max_length=30, choices=DATA_SOURCE_CHOICES, verbose_name='데이터 소스')
    
    # 권한 설정
    accessible_user_types = models.JSONField(
        default=list,
        verbose_name='접근 가능한 사용자 타입',
        help_text='["SUPER_ADMIN", "MANAGER"] 형태로 저장'
    )
    
    # 위젯 설정
    config = models.JSONField(default=dict, verbose_name='위젯 설정')
    refresh_interval = models.IntegerField(default=300, verbose_name='새로고침 간격(초)')
    
    # 레이아웃 설정
    default_width = models.IntegerField(default=4, validators=[MinValueValidator(1), MaxValueValidator(12)], verbose_name='기본 너비')
    default_height = models.IntegerField(default=300, validators=[MinValueValidator(100)], verbose_name='기본 높이')
    
    # 상태
    is_active = models.BooleanField(default=True, verbose_name='활성화')
    is_customizable = models.BooleanField(default=True, verbose_name='사용자 커스터마이징 가능')
    
    # 메타 정보
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='생성자')
    
    class Meta:
        verbose_name = '대시보드 위젯'
        verbose_name_plural = '대시보드 위젯들'
        db_table = 'dashboard_widget'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.title} ({self.get_widget_type_display()})"
    
    def can_access(self, user):
        """사용자의 위젯 접근 권한 확인"""
        if not self.accessible_user_types:
            return True  # 제한 없음
        return user.user_type in self.accessible_user_types


class UserDashboard(models.Model):
    """사용자별 대시보드 설정"""
    
    LAYOUT_TYPE_CHOICES = [
        ('grid', '그리드 레이아웃'),
        ('masonry', '매이슨리 레이아웃'),
        ('fixed', '고정 레이아웃'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='dashboard_settings',
        verbose_name='사용자'
    )
    
    # 레이아웃 설정
    layout_type = models.CharField(
        max_length=20,
        choices=LAYOUT_TYPE_CHOICES,
        default='grid',
        verbose_name='레이아웃 타입'
    )
    
    # 위젯 설정
    widgets = models.ManyToManyField(
        DashboardWidget,
        through='UserWidgetSettings',
        related_name='user_dashboards',
        verbose_name='위젯들'
    )
    
    # 테마 설정
    theme = models.CharField(max_length=20, default='light', verbose_name='테마')
    primary_color = models.CharField(max_length=7, default='#3788d8', verbose_name='기본 색상')
    
    # 알림 설정
    enable_push_notifications = models.BooleanField(default=True, verbose_name='푸시 알림 허용')
    enable_email_notifications = models.BooleanField(default=True, verbose_name='이메일 알림 허용')
    notification_frequency = models.IntegerField(default=60, verbose_name='알림 주기(분)')
    
    # 자동 새로고침 설정
    auto_refresh = models.BooleanField(default=True, verbose_name='자동 새로고침')
    refresh_interval = models.IntegerField(default=300, verbose_name='새로고침 간격(초)')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        verbose_name = '사용자 대시보드 설정'
        verbose_name_plural = '사용자 대시보드 설정들'
        db_table = 'user_dashboard'
    
    def __str__(self):
        return f"{self.user.username}의 대시보드 설정"


class UserWidgetSettings(models.Model):
    """사용자별 위젯 설정"""
    
    dashboard = models.ForeignKey(UserDashboard, on_delete=models.CASCADE, verbose_name='대시보드')
    widget = models.ForeignKey(DashboardWidget, on_delete=models.CASCADE, verbose_name='위젯')
    
    # 위치 설정
    position_x = models.IntegerField(default=0, verbose_name='X 좌표')
    position_y = models.IntegerField(default=0, verbose_name='Y 좌표')
    width = models.IntegerField(default=4, validators=[MinValueValidator(1), MaxValueValidator(12)], verbose_name='너비')
    height = models.IntegerField(default=300, validators=[MinValueValidator(100)], verbose_name='높이')
    
    # 개인 설정
    custom_title = models.CharField(max_length=200, blank=True, verbose_name='커스텀 제목')
    custom_config = models.JSONField(default=dict, verbose_name='커스텀 설정')
    
    # 표시 설정
    is_visible = models.BooleanField(default=True, verbose_name='표시 여부')
    is_minimized = models.BooleanField(default=False, verbose_name='최소화 여부')
    
    # 정렬 순서
    order = models.IntegerField(default=0, verbose_name='정렬 순서')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        verbose_name = '사용자 위젯 설정'
        verbose_name_plural = '사용자 위젯 설정들'
        db_table = 'user_widget_settings'
        unique_together = ['dashboard', 'widget']
        ordering = ['order', 'position_y', 'position_x']
    
    def __str__(self):
        return f"{self.dashboard.user.username} - {self.widget.title}"


class DashboardNotification(models.Model):
    """대시보드 알림"""
    
    NOTIFICATION_TYPE_CHOICES = [
        ('info', '정보'),
        ('warning', '경고'),
        ('error', '오류'),
        ('success', '성공'),
        ('urgent', '긴급'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', '낮음'),
        ('medium', '보통'),
        ('high', '높음'),
        ('critical', '긴급'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 알림 내용
    title = models.CharField(max_length=200, verbose_name='제목')
    message = models.TextField(verbose_name='메시지')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES, verbose_name='알림 유형')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium', verbose_name='우선순위')
    
    # 대상자
    target_users = models.ManyToManyField(User, related_name='dashboard_notifications', verbose_name='대상 사용자')
    target_user_types = models.JSONField(default=list, verbose_name='대상 사용자 타입')
    
    # 관련 데이터
    related_object_type = models.CharField(max_length=50, blank=True, verbose_name='관련 객체 타입')
    related_object_id = models.CharField(max_length=100, blank=True, verbose_name='관련 객체 ID')
    action_url = models.URLField(blank=True, verbose_name='액션 URL')
    
    # 표시 설정
    is_dismissible = models.BooleanField(default=True, verbose_name='닫기 가능')
    auto_dismiss_seconds = models.IntegerField(null=True, blank=True, verbose_name='자동 닫기 시간(초)')
    
    # 발송 설정
    send_push = models.BooleanField(default=True, verbose_name='푸시 알림')
    send_email = models.BooleanField(default=False, verbose_name='이메일 발송')
    
    # 상태
    is_active = models.BooleanField(default=True, verbose_name='활성화')
    scheduled_at = models.DateTimeField(null=True, blank=True, verbose_name='예약 발송 시간')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='발송 시간')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='생성자')
    
    class Meta:
        verbose_name = '대시보드 알림'
        verbose_name_plural = '대시보드 알림들'
        db_table = 'dashboard_notification'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.get_notification_type_display()})"


class NotificationReadStatus(models.Model):
    """알림 읽음 상태"""
    
    notification = models.ForeignKey(DashboardNotification, on_delete=models.CASCADE, verbose_name='알림')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='사용자')
    
    is_read = models.BooleanField(default=False, verbose_name='읽음 여부')
    is_dismissed = models.BooleanField(default=False, verbose_name='닫음 여부')
    
    read_at = models.DateTimeField(null=True, blank=True, verbose_name='읽은 시간')
    dismissed_at = models.DateTimeField(null=True, blank=True, verbose_name='닫은 시간')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    
    class Meta:
        verbose_name = '알림 읽음 상태'
        verbose_name_plural = '알림 읽음 상태들'
        db_table = 'notification_read_status'
        unique_together = ['notification', 'user']
    
    def __str__(self):
        return f"{self.user.username} - {self.notification.title}"


class DashboardDataCache(models.Model):
    """대시보드 데이터 캐시"""
    
    cache_key = models.CharField(max_length=200, unique=True, verbose_name='캐시 키')
    data_source = models.CharField(max_length=50, verbose_name='데이터 소스')
    
    # 캐시된 데이터
    cached_data = models.JSONField(default=dict, verbose_name='캐시된 데이터')
    metadata = models.JSONField(default=dict, verbose_name='메타데이터')
    
    # 캐시 정보
    expires_at = models.DateTimeField(verbose_name='만료 시간')
    hit_count = models.IntegerField(default=0, verbose_name='히트 수')
    last_accessed = models.DateTimeField(auto_now=True, verbose_name='마지막 접근')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        verbose_name = '대시보드 데이터 캐시'
        verbose_name_plural = '대시보드 데이터 캐시들'
        db_table = 'dashboard_data_cache'
        ordering = ['-last_accessed']
    
    def __str__(self):
        return f"{self.cache_key} ({self.data_source})"
    
    @property
    def is_expired(self):
        """캐시 만료 여부 확인"""
        return timezone.now() > self.expires_at
    
    def increment_hit_count(self):
        """히트 수 증가"""
        self.hit_count += 1
        self.save(update_fields=['hit_count', 'last_accessed'])


class SystemHealthMetric(models.Model):
    """시스템 상태 메트릭"""
    
    METRIC_TYPE_CHOICES = [
        ('cpu_usage', 'CPU 사용률'),
        ('memory_usage', '메모리 사용률'),
        ('disk_usage', '디스크 사용률'),
        ('response_time', '응답 시간'),
        ('error_rate', '오류율'),
        ('active_users', '활성 사용자 수'),
        ('notion_sync_status', 'Notion 동기화 상태'),
        ('database_connections', 'DB 연결 수'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    metric_type = models.CharField(max_length=30, choices=METRIC_TYPE_CHOICES, verbose_name='메트릭 타입')
    value = models.FloatField(verbose_name='값')
    unit = models.CharField(max_length=20, default='%', verbose_name='단위')
    
    # 임계값
    warning_threshold = models.FloatField(null=True, blank=True, verbose_name='경고 임계값')
    critical_threshold = models.FloatField(null=True, blank=True, verbose_name='긴급 임계값')
    
    # 메타데이터
    metadata = models.JSONField(default=dict, verbose_name='메타데이터')
    
    recorded_at = models.DateTimeField(auto_now_add=True, verbose_name='기록 시간')
    
    class Meta:
        verbose_name = '시스템 상태 메트릭'
        verbose_name_plural = '시스템 상태 메트릭들'
        db_table = 'system_health_metric'
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['metric_type', '-recorded_at']),
        ]
    
    def __str__(self):
        return f"{self.get_metric_type_display()}: {self.value}{self.unit}"
    
    @property
    def status(self):
        """메트릭 상태 반환"""
        if self.critical_threshold and self.value >= self.critical_threshold:
            return 'critical'
        elif self.warning_threshold and self.value >= self.warning_threshold:
            return 'warning'
        return 'normal'
