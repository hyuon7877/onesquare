"""
OneSquare Time Management - 업무시간 관리 모델

이 모듈은 업무시간 추적 및 관리를 위한 Django 모델들을 정의합니다.
- WorkTimeRecord: 출퇴근 기록
- WorkTimeSettings: 근무시간 기준 설정
- OverTimeRule: 초과근무 규정
- WorkTimeSummary: 근무시간 통계 (캐시)
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
import json

User = get_user_model()


class WorkTimeSettings(models.Model):
    """
    근무시간 기준 설정
    법정 근로시간, 회사 근무시간 규정 관리
    """
    
    class SettingType(models.TextChoices):
        LEGAL = 'legal', '법정 근로시간'
        COMPANY = 'company', '회사 규정'
        DEPARTMENT = 'department', '부서 규정'
        INDIVIDUAL = 'individual', '개인 규정'
    
    # 기본 정보
    name = models.CharField(max_length=100, help_text="설정 이름")
    description = models.TextField(blank=True, help_text="설정 설명")
    setting_type = models.CharField(
        max_length=20,
        choices=SettingType.choices,
        default=SettingType.COMPANY
    )
    
    # 근무시간 기준 (분 단위로 저장)
    daily_standard_minutes = models.IntegerField(
        default=480,  # 8시간 = 480분
        help_text="일 표준 근무시간 (분)"
    )
    weekly_standard_minutes = models.IntegerField(
        default=2400,  # 40시간 = 2400분
        help_text="주 표준 근무시간 (분)"
    )
    monthly_standard_minutes = models.IntegerField(
        default=10400,  # 약 173시간 = 10400분
        help_text="월 표준 근무시간 (분)"
    )
    
    # 허용 시간 설정
    early_arrival_limit_minutes = models.IntegerField(
        default=60,  # 1시간
        help_text="조기출근 허용시간 (분)"
    )
    late_departure_limit_minutes = models.IntegerField(
        default=180,  # 3시간
        help_text="늦은퇴근 허용시간 (분)"
    )
    
    # 휴게시간 설정
    break_time_minutes = models.IntegerField(
        default=60,  # 1시간
        help_text="휴게시간 (분)"
    )
    auto_deduct_break = models.BooleanField(
        default=True,
        help_text="휴게시간 자동 차감 여부"
    )
    
    # 적용 대상
    target_users = models.ManyToManyField(
        User,
        blank=True,
        related_name='work_time_settings',
        help_text="적용 대상 사용자"
    )
    
    # 유효성
    is_active = models.BooleanField(default=True)
    effective_from = models.DateField(help_text="적용 시작일")
    effective_until = models.DateField(
        null=True, blank=True,
        help_text="적용 종료일"
    )
    
    # Notion 연동
    notion_database_id = models.CharField(
        max_length=36,
        blank=True,
        help_text="Notion 데이터베이스 ID"
    )
    notion_page_id = models.CharField(
        max_length=36,
        blank=True,
        help_text="Notion 페이지 ID"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_work_settings'
    )
    
    class Meta:
        verbose_name = "근무시간 설정"
        verbose_name_plural = "근무시간 설정 목록"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_setting_type_display()})"
    
    @property
    def daily_standard_hours(self):
        """일 표준 근무시간 (시간)"""
        return self.daily_standard_minutes / 60
    
    @property
    def weekly_standard_hours(self):
        """주 표준 근무시간 (시간)"""
        return self.weekly_standard_minutes / 60
    
    def clean(self):
        """모델 유효성 검사"""
        if self.effective_until and self.effective_from > self.effective_until:
            raise ValidationError("종료일은 시작일 이후여야 합니다.")


class WorkTimeRecord(models.Model):
    """
    출퇴근 기록
    실제 근무시간 데이터 저장 및 Notion 동기화
    """
    
    class RecordStatus(models.TextChoices):
        DRAFT = 'draft', '임시저장'
        CONFIRMED = 'confirmed', '확정'
        APPROVED = 'approved', '승인됨'
        REJECTED = 'rejected', '반려됨'
        MODIFIED = 'modified', '수정됨'
    
    class RecordType(models.TextChoices):
        NORMAL = 'normal', '일반 근무'
        OVERTIME = 'overtime', '초과 근무'
        HOLIDAY = 'holiday', '휴일 근무'
        NIGHT = 'night', '야간 근무'
        REMOTE = 'remote', '재택 근무'
    
    # 기본 정보
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='work_time_records',
        help_text="사용자"
    )
    work_date = models.DateField(help_text="근무일")
    record_type = models.CharField(
        max_length=20,
        choices=RecordType.choices,
        default=RecordType.NORMAL
    )
    
    # 시간 기록
    check_in_time = models.DateTimeField(
        null=True, blank=True,
        help_text="출근 시간"
    )
    check_out_time = models.DateTimeField(
        null=True, blank=True,
        help_text="퇴근 시간"
    )
    
    # 계산된 시간 (분 단위)
    total_work_minutes = models.IntegerField(
        default=0,
        help_text="총 근무시간 (분)"
    )
    break_minutes = models.IntegerField(
        default=0,
        help_text="휴게시간 (분)"
    )
    actual_work_minutes = models.IntegerField(
        default=0,
        help_text="실제 근무시간 (분, 휴게시간 제외)"
    )
    overtime_minutes = models.IntegerField(
        default=0,
        help_text="초과 근무시간 (분)"
    )
    
    # 위치 정보 (선택적)
    check_in_location = models.JSONField(
        default=dict,
        blank=True,
        help_text="출근 위치 정보 (GPS 좌표 등)"
    )
    check_out_location = models.JSONField(
        default=dict,
        blank=True,
        help_text="퇴근 위치 정보 (GPS 좌표 등)"
    )
    
    # 메모 및 사유
    memo = models.TextField(blank=True, help_text="메모")
    adjustment_reason = models.TextField(
        blank=True,
        help_text="시간 조정 사유"
    )
    
    # 승인 상태
    status = models.CharField(
        max_length=20,
        choices=RecordStatus.choices,
        default=RecordStatus.DRAFT
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_work_records',
        help_text="승인자"
    )
    approved_at = models.DateTimeField(
        null=True, blank=True,
        help_text="승인 시간"
    )
    
    # Notion 동기화
    notion_page_id = models.CharField(
        max_length=36,
        blank=True,
        help_text="Notion 페이지 ID"
    )
    notion_last_synced = models.DateTimeField(
        null=True, blank=True,
        help_text="Notion 마지막 동기화 시간"
    )
    is_notion_synced = models.BooleanField(
        default=False,
        help_text="Notion 동기화 완료 여부"
    )
    
    # 시스템 필드
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "근무시간 기록"
        verbose_name_plural = "근무시간 기록 목록"
        ordering = ['-work_date', '-check_in_time']
        unique_together = ['user', 'work_date']
        indexes = [
            models.Index(fields=['user', 'work_date']),
            models.Index(fields=['work_date', 'status']),
            models.Index(fields=['is_notion_synced']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.work_date}"
    
    def clean(self):
        """모델 유효성 검사"""
        if self.check_in_time and self.check_out_time:
            if self.check_in_time >= self.check_out_time:
                raise ValidationError("퇴근 시간은 출근 시간 이후여야 합니다.")
    
    def save(self, *args, **kwargs):
        """저장 시 자동 계산 수행"""
        self.calculate_work_times()
        super().save(*args, **kwargs)
    
    def calculate_work_times(self):
        """근무시간 자동 계산"""
        if not (self.check_in_time and self.check_out_time):
            return
        
        # 총 근무시간 계산 (분)
        time_diff = self.check_out_time - self.check_in_time
        self.total_work_minutes = int(time_diff.total_seconds() / 60)
        
        # 휴게시간 처리 (8시간 이상 근무 시 1시간 자동 차감)
        if self.total_work_minutes >= 480:  # 8시간
            self.break_minutes = 60  # 1시간
        else:
            self.break_minutes = 0
        
        # 실제 근무시간 = 총 근무시간 - 휴게시간
        self.actual_work_minutes = max(0, self.total_work_minutes - self.break_minutes)
        
        # 초과근무시간 계산 (8시간 기준)
        standard_minutes = 480  # 8시간
        self.overtime_minutes = max(0, self.actual_work_minutes - standard_minutes)
    
    @property
    def total_work_hours(self):
        """총 근무시간 (시간, 소수점)"""
        return round(self.total_work_minutes / 60, 2)
    
    @property
    def actual_work_hours(self):
        """실제 근무시간 (시간, 소수점)"""
        return round(self.actual_work_minutes / 60, 2)
    
    @property
    def overtime_hours(self):
        """초과 근무시간 (시간, 소수점)"""
        return round(self.overtime_minutes / 60, 2)
    
    @property
    def is_overtime(self):
        """초과근무 여부"""
        return self.overtime_minutes > 0
    
    @property
    def is_undertime(self):
        """미달근무 여부 (8시간 기준)"""
        return self.actual_work_minutes < 480
    
    def get_work_time_formatted(self):
        """근무시간 포맷팅 (HH:MM)"""
        hours = self.actual_work_minutes // 60
        minutes = self.actual_work_minutes % 60
        return f"{hours:02d}:{minutes:02d}"
    
    def to_notion_properties(self):
        """Notion 페이지 속성으로 변환"""
        return {
            "Date": {
                "date": {
                    "start": self.work_date.isoformat()
                }
            },
            "User": {
                "rich_text": [
                    {
                        "text": {
                            "content": str(self.user.get_full_name() or self.user.username)
                        }
                    }
                ]
            },
            "Check In": {
                "rich_text": [
                    {
                        "text": {
                            "content": self.check_in_time.strftime("%H:%M") if self.check_in_time else ""
                        }
                    }
                ]
            },
            "Check Out": {
                "rich_text": [
                    {
                        "text": {
                            "content": self.check_out_time.strftime("%H:%M") if self.check_out_time else ""
                        }
                    }
                ]
            },
            "Total Hours": {
                "number": self.total_work_hours
            },
            "Actual Hours": {
                "number": self.actual_work_hours
            },
            "Overtime Hours": {
                "number": self.overtime_hours
            },
            "Status": {
                "select": {
                    "name": self.get_status_display()
                }
            },
            "Type": {
                "select": {
                    "name": self.get_record_type_display()
                }
            },
            "Memo": {
                "rich_text": [
                    {
                        "text": {
                            "content": self.memo or ""
                        }
                    }
                ]
            }
        }


class WorkTimeSummary(models.Model):
    """
    근무시간 통계 요약
    성능 최적화를 위한 주간/월간 통계 캐시
    """
    
    class SummaryType(models.TextChoices):
        DAILY = 'daily', '일간'
        WEEKLY = 'weekly', '주간'
        MONTHLY = 'monthly', '월간'
        YEARLY = 'yearly', '연간'
    
    # 기본 정보
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='work_time_summaries'
    )
    summary_type = models.CharField(
        max_length=20,
        choices=SummaryType.choices
    )
    
    # 기간 정보
    year = models.IntegerField()
    month = models.IntegerField(null=True, blank=True)  # 월간/일간용
    week = models.IntegerField(null=True, blank=True)   # 주간용
    day = models.IntegerField(null=True, blank=True)    # 일간용
    
    # 통계 데이터 (분 단위)
    total_work_minutes = models.IntegerField(default=0)
    actual_work_minutes = models.IntegerField(default=0)
    overtime_minutes = models.IntegerField(default=0)
    standard_work_minutes = models.IntegerField(default=0)
    
    # 출근 통계
    work_days = models.IntegerField(default=0, help_text="실제 출근일수")
    expected_work_days = models.IntegerField(default=0, help_text="예상 출근일수")
    late_count = models.IntegerField(default=0, help_text="지각 횟수")
    early_leave_count = models.IntegerField(default=0, help_text="조퇴 횟수")
    
    # Notion 동기화
    notion_page_id = models.CharField(
        max_length=36,
        blank=True
    )
    
    # 시스템 필드
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "근무시간 요약"
        verbose_name_plural = "근무시간 요약 목록"
        unique_together = ['user', 'summary_type', 'year', 'month', 'week', 'day']
        indexes = [
            models.Index(fields=['user', 'summary_type', 'year', 'month']),
            models.Index(fields=['updated_at']),
        ]
    
    def __str__(self):
        period_str = f"{self.year}"
        if self.month:
            period_str += f"-{self.month:02d}"
        if self.day:
            period_str += f"-{self.day:02d}"
        if self.week:
            period_str += f" W{self.week}"
        
        return f"{self.user.username} {self.get_summary_type_display()} {period_str}"
    
    @property
    def total_work_hours(self):
        """총 근무시간 (시간)"""
        return round(self.total_work_minutes / 60, 2)
    
    @property
    def actual_work_hours(self):
        """실제 근무시간 (시간)"""
        return round(self.actual_work_minutes / 60, 2)
    
    @property
    def overtime_hours(self):
        """초과 근무시간 (시간)"""
        return round(self.overtime_minutes / 60, 2)
    
    @property
    def standard_work_hours(self):
        """표준 근무시간 (시간)"""
        return round(self.standard_work_minutes / 60, 2)
    
    @property
    def work_rate(self):
        """근무율 (%)"""
        if self.expected_work_days == 0:
            return 0
        return round((self.work_days / self.expected_work_days) * 100, 1)
    
    @property
    def overtime_rate(self):
        """초과근무율 (%)"""
        if self.standard_work_minutes == 0:
            return 0
        return round((self.overtime_minutes / self.standard_work_minutes) * 100, 1)
    
    def calculate_from_records(self, records_queryset):
        """근무 기록으로부터 통계 계산"""
        self.work_days = records_queryset.filter(
            check_in_time__isnull=False,
            check_out_time__isnull=False
        ).count()
        
        # 집계 계산
        from django.db.models import Sum
        aggregates = records_queryset.aggregate(
            total_work=Sum('total_work_minutes'),
            actual_work=Sum('actual_work_minutes'),
            overtime=Sum('overtime_minutes')
        )
        
        self.total_work_minutes = aggregates['total_work'] or 0
        self.actual_work_minutes = aggregates['actual_work'] or 0
        self.overtime_minutes = aggregates['overtime'] or 0
        
        # 지각/조퇴 계산 (9시 출근, 18시 퇴근 기준)
        from datetime import time
        standard_start = time(9, 0)
        standard_end = time(18, 0)
        
        self.late_count = records_queryset.filter(
            check_in_time__time__gt=standard_start
        ).count()
        
        self.early_leave_count = records_queryset.filter(
            check_out_time__time__lt=standard_end
        ).count()


class OverTimeRule(models.Model):
    """
    초과근무 규정
    초과근무 승인 및 수당 계산 규칙
    """
    
    class RuleType(models.TextChoices):
        DAILY = 'daily', '일일 초과근무'
        WEEKLY = 'weekly', '주간 초과근무'
        HOLIDAY = 'holiday', '휴일근무'
        NIGHT = 'night', '야간근무'
    
    # 기본 정보
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    rule_type = models.CharField(
        max_length=20,
        choices=RuleType.choices
    )
    
    # 기준 시간 (분)
    threshold_minutes = models.IntegerField(
        help_text="초과근무 기준시간 (분)"
    )
    
    # 수당 비율
    pay_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.5'),
        help_text="수당 비율 (1.5 = 150%)"
    )
    
    # 승인 설정
    requires_approval = models.BooleanField(
        default=True,
        help_text="사전 승인 필요 여부"
    )
    max_overtime_minutes = models.IntegerField(
        default=180,  # 3시간
        help_text="최대 초과근무 시간 (분)"
    )
    
    # 적용 대상
    target_users = models.ManyToManyField(
        User,
        blank=True,
        related_name='overtime_rules'
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "초과근무 규정"
        verbose_name_plural = "초과근무 규정 목록"
    
    def __str__(self):
        return f"{self.name} ({self.get_rule_type_display()})"
    
    def calculate_overtime_pay(self, overtime_minutes, hourly_rate):
        """초과근무 수당 계산"""
        if overtime_minutes <= 0:
            return Decimal('0')
        
        overtime_hours = Decimal(str(overtime_minutes / 60))
        base_pay = overtime_hours * hourly_rate
        overtime_pay = base_pay * self.pay_rate
        
        return overtime_pay.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
