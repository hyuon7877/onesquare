from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta, date
import json

User = get_user_model()


class LeaveType(models.Model):
    """연차 유형 정의"""
    LEAVE_TYPES = [
        ('annual', '연차'),
        ('sick', '병가'),
        ('special', '특별휴가'),
        ('half_day', '반차'),
        ('replacement', '대체휴무'),
    ]
    
    name = models.CharField(max_length=50, choices=LEAVE_TYPES, unique=True)
    description = models.TextField(blank=True)
    max_days = models.PositiveIntegerField(null=True, blank=True)
    requires_approval = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '연차 유형'
        verbose_name_plural = '연차 유형들'
    
    def __str__(self):
        return self.get_name_display()


class LeaveBalance(models.Model):
    """사용자별 연차 잔여일수 관리"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='leave_balance')
    year = models.PositiveIntegerField(default=timezone.now().year)
    total_annual_days = models.DecimalField(max_digits=5, decimal_places=1, default=15.0)
    used_annual_days = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    remaining_annual_days = models.DecimalField(max_digits=5, decimal_places=1, default=15.0)
    carry_over_days = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    notion_database_id = models.CharField(max_length=255, blank=True)
    notion_sync_status = models.CharField(max_length=50, default='pending')
    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '연차 잔여일수'
        verbose_name_plural = '연차 잔여일수'
        unique_together = ['user', 'year']
    
    def __str__(self):
        return f"{self.user.username} - {self.year}년 (잔여: {self.remaining_annual_days}일)"
    
    def recalculate_balance(self):
        """잔여 연차 재계산"""
        self.remaining_annual_days = self.total_annual_days + self.carry_over_days - self.used_annual_days
        self.save()
    
    def deduct_leave(self, days):
        """연차 차감"""
        if self.remaining_annual_days < days:
            raise ValidationError("잔여 연차가 부족합니다.")
        self.used_annual_days += days
        self.remaining_annual_days -= days
        self.save()
    
    def restore_leave(self, days):
        """연차 복구 (취소 시)"""
        self.used_annual_days -= days
        self.remaining_annual_days += days
        self.save()


class LeaveRequest(models.Model):
    """연차 신청 관리"""
    STATUS_CHOICES = [
        ('pending', '대기중'),
        ('approved', '승인됨'),
        ('rejected', '반려됨'),
        ('cancelled', '취소됨'),
    ]
    
    # 기본 정보
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    is_half_day_start = models.BooleanField(default=False)
    is_half_day_end = models.BooleanField(default=False)
    
    # 신청 상세
    reason = models.TextField()
    attachment = models.FileField(upload_to='leave_attachments/', null=True, blank=True)
    emergency_contact = models.CharField(max_length=50, blank=True)
    
    # 승인 정보
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_leaves')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # 계산 필드
    total_days = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    
    # Notion 동기화
    notion_page_id = models.CharField(max_length=255, blank=True)
    notion_sync_status = models.CharField(max_length=50, default='pending')
    last_synced_at = models.DateTimeField(null=True, blank=True)
    
    # 메타데이터
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # 오프라인 지원
    is_offline_created = models.BooleanField(default=False)
    offline_sync_data = models.JSONField(null=True, blank=True)
    
    class Meta:
        verbose_name = '연차 신청'
        verbose_name_plural = '연차 신청들'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['approver', 'status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.start_date} ~ {self.end_date} ({self.get_status_display()})"
    
    def clean(self):
        """유효성 검증"""
        if self.start_date > self.end_date:
            raise ValidationError("시작일이 종료일보다 늦을 수 없습니다.")
        
        # 중복 신청 체크
        overlapping = LeaveRequest.objects.filter(
            user=self.user,
            status__in=['pending', 'approved']
        ).exclude(pk=self.pk)
        
        for req in overlapping:
            if (self.start_date <= req.end_date and self.end_date >= req.start_date):
                raise ValidationError("해당 기간에 이미 신청된 연차가 있습니다.")
    
    def calculate_total_days(self):
        """총 연차 일수 계산"""
        if self.start_date == self.end_date:
            if self.is_half_day_start or self.is_half_day_end:
                return 0.5
            return 1.0
        
        # 주말 제외 계산
        current_date = self.start_date
        total = 0
        
        while current_date <= self.end_date:
            if current_date.weekday() < 5:  # 월-금
                if current_date == self.start_date and self.is_half_day_start:
                    total += 0.5
                elif current_date == self.end_date and self.is_half_day_end:
                    total += 0.5
                else:
                    total += 1
            current_date += timedelta(days=1)
        
        return total
    
    def save(self, *args, **kwargs):
        # 총 일수 자동 계산
        self.total_days = self.calculate_total_days()
        super().save(*args, **kwargs)
    
    def approve(self, approver):
        """연차 승인 처리"""
        if self.status != 'pending':
            raise ValidationError("대기중인 신청만 승인할 수 있습니다.")
        
        # 잔여 연차 확인
        balance = LeaveBalance.objects.get_or_create(
            user=self.user,
            year=self.start_date.year
        )[0]
        
        if balance.remaining_annual_days < self.total_days:
            raise ValidationError("잔여 연차가 부족합니다.")
        
        # 승인 처리
        self.status = 'approved'
        self.approver = approver
        self.approved_at = timezone.now()
        self.save()
        
        # 연차 차감
        balance.deduct_leave(self.total_days)
    
    def reject(self, approver, reason=""):
        """연차 반려 처리"""
        if self.status != 'pending':
            raise ValidationError("대기중인 신청만 반려할 수 있습니다.")
        
        self.status = 'rejected'
        self.approver = approver
        self.rejection_reason = reason
        self.save()
    
    def cancel(self):
        """연차 취소 처리"""
        if self.status == 'approved':
            # 승인된 연차 취소 시 연차 복구
            balance = LeaveBalance.objects.get(
                user=self.user,
                year=self.start_date.year
            )
            balance.restore_leave(self.total_days)
        
        self.status = 'cancelled'
        self.save()


class Holiday(models.Model):
    """공휴일 및 회사 휴무일 관리"""
    date = models.DateField(unique=True)
    name = models.CharField(max_length=100)
    is_company_holiday = models.BooleanField(default=False)
    is_public_holiday = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    
    # Notion 동기화
    notion_page_id = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '휴일'
        verbose_name_plural = '휴일들'
        ordering = ['date']
    
    def __str__(self):
        return f"{self.date} - {self.name}"
