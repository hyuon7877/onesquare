"""
모니터링 데이터 모델
실시간 모니터링 데이터 저장 및 분석을 위한 모델들
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime, timedelta
import json

User = get_user_model()


class SystemMetrics(models.Model):
    """시스템 성능 지표"""
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    cpu_percent = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    memory_percent = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    memory_available_gb = models.FloatField(validators=[MinValueValidator(0)])
    disk_usage_percent = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    disk_free_gb = models.FloatField(validators=[MinValueValidator(0)])
    network_bytes_sent = models.BigIntegerField(default=0)
    network_bytes_recv = models.BigIntegerField(default=0)
    
    # Django 프로세스 특화 지표
    django_cpu_percent = models.FloatField(validators=[MinValueValidator(0)])
    django_memory_percent = models.FloatField(validators=[MinValueValidator(0)])
    django_memory_rss_mb = models.FloatField(validators=[MinValueValidator(0)])
    django_threads_count = models.IntegerField(default=0)
    django_open_files = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['cpu_percent']),
            models.Index(fields=['memory_percent']),
        ]
    
    def __str__(self):
        return f"System Metrics {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    
    @classmethod
    def get_recent_metrics(cls, hours=1):
        """최근 N시간의 메트릭스 반환"""
        since = datetime.now() - timedelta(hours=hours)
        return cls.objects.filter(timestamp__gte=since).order_by('timestamp')
    
    @classmethod
    def get_average_metrics(cls, hours=24):
        """평균 메트릭스 계산"""
        metrics = cls.get_recent_metrics(hours)
        if not metrics.exists():
            return None
        
        from django.db.models import Avg
        return metrics.aggregate(
            avg_cpu=Avg('cpu_percent'),
            avg_memory=Avg('memory_percent'),
            avg_django_cpu=Avg('django_cpu_percent'),
            avg_django_memory=Avg('django_memory_percent')
        )


class RequestMetrics(models.Model):
    """요청별 성능 지표"""
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=500, db_index=True)
    url_pattern = models.CharField(max_length=200, blank=True)
    view_name = models.CharField(max_length=200, blank=True)
    status_code = models.IntegerField(db_index=True)
    response_time_ms = models.FloatField(validators=[MinValueValidator(0)])
    memory_diff_mb = models.FloatField(default=0)
    content_length = models.IntegerField(default=0)
    
    # 사용자 정보
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=500, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['path']),
            models.Index(fields=['status_code']),
            models.Index(fields=['response_time_ms']),
            models.Index(fields=['user', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.method} {self.path} - {self.response_time_ms}ms"
    
    @classmethod
    def get_slow_requests(cls, threshold_ms=500, hours=24):
        """느린 요청들 반환"""
        since = datetime.now() - timedelta(hours=hours)
        return cls.objects.filter(
            timestamp__gte=since,
            response_time_ms__gt=threshold_ms
        ).order_by('-response_time_ms')
    
    @classmethod
    def get_error_requests(cls, hours=24):
        """에러 요청들 반환"""
        since = datetime.now() - timedelta(hours=hours)
        return cls.objects.filter(
            timestamp__gte=since,
            status_code__gte=400
        ).order_by('-timestamp')
    
    @classmethod
    def get_popular_endpoints(cls, hours=24, limit=10):
        """인기 엔드포인트 반환"""
        from django.db.models import Count
        since = datetime.now() - timedelta(hours=hours)
        return cls.objects.filter(timestamp__gte=since).values('path').annotate(
            request_count=Count('id')
        ).order_by('-request_count')[:limit]


class UserActivity(models.Model):
    """사용자 활동 로그"""
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, db_index=True, blank=True)
    path = models.CharField(max_length=500)
    method = models.CharField(max_length=10)
    status_code = models.IntegerField()
    duration_ms = models.FloatField(validators=[MinValueValidator(0)])
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=500, blank=True)
    
    # 활동 분류
    is_authenticated = models.BooleanField(default=False, db_index=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['session_key', 'timestamp']),
            models.Index(fields=['is_authenticated', 'timestamp']),
        ]
    
    def __str__(self):
        user_str = self.user.username if self.user else 'Anonymous'
        return f"{user_str} - {self.path} ({self.timestamp.strftime('%H:%M:%S')})"
    
    @classmethod
    def get_user_sessions(cls, user, hours=24):
        """사용자 세션 활동 반환"""
        since = datetime.now() - timedelta(hours=hours)
        return cls.objects.filter(
            user=user,
            timestamp__gte=since
        ).order_by('timestamp')
    
    @classmethod
    def get_active_users(cls, hours=1):
        """최근 활성 사용자 수"""
        since = datetime.now() - timedelta(hours=hours)
        return cls.objects.filter(
            timestamp__gte=since,
            is_authenticated=True
        ).values('user').distinct().count()


class NotionAPIMetrics(models.Model):
    """Notion API 호출 지표"""
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    endpoint = models.CharField(max_length=200)
    method = models.CharField(max_length=10)
    status_code = models.IntegerField(db_index=True)
    response_time_ms = models.FloatField(validators=[MinValueValidator(0)])
    request_size_bytes = models.IntegerField(default=0)
    response_size_bytes = models.IntegerField(default=0)
    
    # 성공/실패 분류
    is_success = models.BooleanField(db_index=True)
    error_message = models.TextField(blank=True)
    
    # 요청 컨텍스트
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    operation_type = models.CharField(max_length=50, blank=True)  # query, create, update, delete
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['endpoint']),
            models.Index(fields=['is_success', 'timestamp']),
            models.Index(fields=['operation_type', 'timestamp']),
        ]
    
    def __str__(self):
        status = "SUCCESS" if self.is_success else "FAILED"
        return f"{self.endpoint} - {status} ({self.response_time_ms}ms)"
    
    @classmethod
    def get_success_rate(cls, hours=24):
        """성공률 계산"""
        since = datetime.now() - timedelta(hours=hours)
        total = cls.objects.filter(timestamp__gte=since).count()
        if total == 0:
            return 100.0
        
        success = cls.objects.filter(timestamp__gte=since, is_success=True).count()
        return round((success / total) * 100, 2)
    
    @classmethod
    def get_average_response_time(cls, hours=24):
        """평균 응답 시간 계산"""
        from django.db.models import Avg
        since = datetime.now() - timedelta(hours=hours)
        result = cls.objects.filter(timestamp__gte=since).aggregate(
            avg_time=Avg('response_time_ms')
        )
        return round(result['avg_time'] or 0, 2)
    
    @classmethod
    def get_error_summary(cls, hours=24):
        """에러 요약 반환"""
        from django.db.models import Count
        since = datetime.now() - timedelta(hours=hours)
        return cls.objects.filter(
            timestamp__gte=since,
            is_success=False
        ).values('status_code', 'error_message').annotate(
            count=Count('id')
        ).order_by('-count')


class ErrorLog(models.Model):
    """에러 로그"""
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    error_type = models.CharField(max_length=100, db_index=True)  # http_error, exception, etc.
    level = models.CharField(max_length=20, db_index=True)  # ERROR, WARNING, CRITICAL
    
    # 에러 상세 정보
    message = models.TextField()
    path = models.CharField(max_length=500, blank=True)
    method = models.CharField(max_length=10, blank=True)
    status_code = models.IntegerField(null=True, blank=True)
    
    # 컨텍스트 정보
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    
    # 기술적 세부사항
    exception_type = models.CharField(max_length=100, blank=True)
    stack_trace = models.TextField(blank=True)
    extra_data = models.JSONField(default=dict)
    
    # 해결 상태
    is_resolved = models.BooleanField(default=False, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_errors')
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['error_type']),
            models.Index(fields=['level']),
            models.Index(fields=['is_resolved', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.error_type} - {self.message[:100]}"
    
    @classmethod
    def get_unresolved_errors(cls):
        """미해결 에러 반환"""
        return cls.objects.filter(is_resolved=False).order_by('-timestamp')
    
    @classmethod
    def get_error_frequency(cls, hours=24):
        """에러 빈도 분석"""
        from django.db.models import Count
        since = datetime.now() - timedelta(hours=hours)
        return cls.objects.filter(timestamp__gte=since).values('error_type').annotate(
            count=Count('id')
        ).order_by('-count')
    
    def mark_resolved(self, user=None):
        """에러를 해결됨으로 표시"""
        self.is_resolved = True
        self.resolved_at = datetime.now()
        self.resolved_by = user
        self.save(update_fields=['is_resolved', 'resolved_at', 'resolved_by'])


class PerformanceAlert(models.Model):
    """성능 알림"""
    ALERT_TYPES = [
        ('cpu', 'High CPU Usage'),
        ('memory', 'High Memory Usage'),
        ('disk', 'High Disk Usage'),
        ('slow_request', 'Slow Request'),
        ('error_rate', 'High Error Rate'),
        ('notion_api', 'Notion API Issue'),
    ]
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES, db_index=True)
    severity = models.CharField(max_length=20, choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], db_index=True)
    
    message = models.TextField()
    threshold_value = models.FloatField(null=True, blank=True)
    actual_value = models.FloatField(null=True, blank=True)
    
    # 관련 메트릭 참조
    related_path = models.CharField(max_length=500, blank=True)
    related_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # 알림 상태
    is_acknowledged = models.BooleanField(default=False, db_index=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='acknowledged_alerts')
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['alert_type']),
            models.Index(fields=['severity']),
            models.Index(fields=['is_acknowledged', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.severity.upper()}"
    
    @classmethod
    def get_unacknowledged_alerts(cls):
        """미확인 알림 반환"""
        return cls.objects.filter(is_acknowledged=False).order_by('-timestamp')
    
    @classmethod
    def create_alert(cls, alert_type, severity, message, **kwargs):
        """새 알림 생성"""
        return cls.objects.create(
            alert_type=alert_type,
            severity=severity,
            message=message,
            **kwargs
        )
    
    def acknowledge(self, user=None):
        """알림을 확인됨으로 표시"""
        self.is_acknowledged = True
        self.acknowledged_at = datetime.now()
        self.acknowledged_by = user
        self.save(update_fields=['is_acknowledged', 'acknowledged_at', 'acknowledged_by'])