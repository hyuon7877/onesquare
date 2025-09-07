"""
OneSquare 매출 관리 시스템 - Django 모델
Notion API와 연동하여 매출 데이터를 관리하는 모델들
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.conf import settings
from decimal import Decimal
import uuid
from datetime import datetime

class RevenueCategory(models.Model):
    """매출 카테고리"""
    CATEGORY_CHOICES = [
        ('project', '프로젝트 매출'),
        ('service', '서비스 매출'),  
        ('product', '제품 매출'),
        ('consulting', '컨설팅 매출'),
        ('maintenance', '유지보수 매출'),
        ('other', '기타 매출'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name='카테고리명')
    code = models.CharField(max_length=20, unique=True, verbose_name='카테고리 코드')
    category_type = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name='카테고리 유형')
    description = models.TextField(blank=True, verbose_name='설명')
    is_active = models.BooleanField(default=True, verbose_name='활성 상태')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'revenue_category'
        verbose_name = '매출 카테고리'
        verbose_name_plural = '매출 카테고리들'
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"

class Client(models.Model):
    """고객/클라이언트"""
    CLIENT_TYPE_CHOICES = [
        ('corporate', '기업'),
        ('individual', '개인'),
        ('government', '정부기관'),
        ('ngo', '비영리단체'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name='고객명')
    code = models.CharField(max_length=50, unique=True, verbose_name='고객 코드')
    client_type = models.CharField(max_length=20, choices=CLIENT_TYPE_CHOICES, verbose_name='고객 유형')
    business_number = models.CharField(max_length=20, blank=True, verbose_name='사업자번호')
    contact_person = models.CharField(max_length=100, blank=True, verbose_name='담당자')
    phone = models.CharField(max_length=20, blank=True, verbose_name='연락처')
    email = models.EmailField(blank=True, verbose_name='이메일')
    address = models.TextField(blank=True, verbose_name='주소')
    
    # Notion 연동
    notion_page_id = models.CharField(max_length=50, blank=True, verbose_name='Notion 페이지 ID')
    notion_database_id = models.CharField(max_length=50, blank=True, verbose_name='Notion 데이터베이스 ID')
    
    is_active = models.BooleanField(default=True, verbose_name='활성 상태')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'client'
        verbose_name = '고객'
        verbose_name_plural = '고객들'
        ordering = ['code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"

class Project(models.Model):
    """프로젝트"""
    STATUS_CHOICES = [
        ('planning', '기획 단계'),
        ('in_progress', '진행 중'),
        ('completed', '완료'),
        ('cancelled', '취소'),
        ('on_hold', '보류'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name='프로젝트명')
    code = models.CharField(max_length=50, unique=True, verbose_name='프로젝트 코드')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name='고객')
    category = models.ForeignKey(RevenueCategory, on_delete=models.CASCADE, verbose_name='매출 카테고리')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning', verbose_name='상태')
    start_date = models.DateField(verbose_name='시작일')
    end_date = models.DateField(verbose_name='종료일')
    contract_amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0'))], verbose_name='계약금액')
    
    # 담당자
    project_manager = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, 
                                      related_name='managed_projects', verbose_name='프로젝트 매니저')
    team_members = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='project_teams', verbose_name='팀원들')
    
    # Notion 연동
    notion_page_id = models.CharField(max_length=50, blank=True, verbose_name='Notion 페이지 ID')
    notion_database_id = models.CharField(max_length=50, blank=True, verbose_name='Notion 데이터베이스 ID')
    
    description = models.TextField(blank=True, verbose_name='프로젝트 설명')
    notes = models.TextField(blank=True, verbose_name='메모')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'project'
        verbose_name = '프로젝트'
        verbose_name_plural = '프로젝트들'
        ordering = ['-start_date', 'code']
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def total_revenue(self):
        """프로젝트 총 매출"""
        return self.revenue_records.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0')
    
    @property
    def completion_rate(self):
        """프로젝트 완료율 (매출 기준)"""
        if self.contract_amount > 0:
            return float(self.total_revenue / self.contract_amount * 100)
        return 0

class RevenueRecord(models.Model):
    """매출 기록"""
    REVENUE_TYPE_CHOICES = [
        ('contract', '계약금'),
        ('milestone', '마일스톤'),
        ('monthly', '월 매출'),
        ('final', '최종 매출'),
        ('bonus', '보너스'),
        ('penalty', '페널티'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', '미수금'),
        ('partial', '부분 수금'),
        ('completed', '수금 완료'),
        ('overdue', '연체'),
        ('cancelled', '취소'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 기본 정보
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='revenue_records', verbose_name='프로젝트')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, verbose_name='고객')
    category = models.ForeignKey(RevenueCategory, on_delete=models.CASCADE, verbose_name='매출 카테고리')
    
    # 매출 정보
    revenue_type = models.CharField(max_length=20, choices=REVENUE_TYPE_CHOICES, verbose_name='매출 유형')
    amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0'))], verbose_name='매출 금액')
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0'), verbose_name='세금')
    net_amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='순 매출액')
    
    # 일자 정보
    revenue_date = models.DateField(verbose_name='매출 발생일')
    invoice_date = models.DateField(blank=True, null=True, verbose_name='청구일')
    due_date = models.DateField(blank=True, null=True, verbose_name='수금 예정일')
    payment_date = models.DateField(blank=True, null=True, verbose_name='실제 수금일')
    
    # 상태 정보
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending', verbose_name='수금 상태')
    is_confirmed = models.BooleanField(default=False, verbose_name='확정 여부')
    
    # 담당자
    sales_person = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='sales_records', verbose_name='영업 담당자')
    
    # Notion 연동
    notion_page_id = models.CharField(max_length=50, blank=True, verbose_name='Notion 페이지 ID')
    notion_database_id = models.CharField(max_length=50, blank=True, verbose_name='Notion 데이터베이스 ID')
    last_synced_at = models.DateTimeField(blank=True, null=True, verbose_name='마지막 동기화')
    
    # 메타 정보
    description = models.TextField(blank=True, verbose_name='설명')
    notes = models.TextField(blank=True, verbose_name='메모')
    invoice_number = models.CharField(max_length=50, blank=True, verbose_name='청구서 번호')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, 
                                 related_name='created_revenues', verbose_name='등록자')
    
    class Meta:
        db_table = 'revenue_record'
        verbose_name = '매출 기록'
        verbose_name_plural = '매출 기록들'
        ordering = ['-revenue_date', '-created_at']
        indexes = [
            models.Index(fields=['revenue_date']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['project', 'revenue_date']),
            models.Index(fields=['client', 'revenue_date']),
            models.Index(fields=['notion_page_id']),
        ]
    
    def __str__(self):
        return f"{self.project.code} - {self.amount:,}원 ({self.revenue_date})"
    
    def save(self, *args, **kwargs):
        # 순 매출액 자동 계산
        if not self.net_amount:
            self.net_amount = self.amount - self.tax_amount
        
        # 수금일이 설정되면 상태를 완료로 변경
        if self.payment_date and self.payment_status == 'pending':
            self.payment_status = 'completed'
        
        super().save(*args, **kwargs)

class RevenueTarget(models.Model):
    """매출 목표"""
    TARGET_TYPE_CHOICES = [
        ('monthly', '월별'),
        ('quarterly', '분기별'),
        ('yearly', '연간'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 목표 기간
    target_type = models.CharField(max_length=20, choices=TARGET_TYPE_CHOICES, verbose_name='목표 유형')
    year = models.IntegerField(verbose_name='년도')
    month = models.IntegerField(blank=True, null=True, verbose_name='월 (월별 목표인 경우)')
    quarter = models.IntegerField(blank=True, null=True, verbose_name='분기 (분기별 목표인 경우)')
    
    # 목표 금액
    target_amount = models.DecimalField(max_digits=15, decimal_places=2, 
                                      validators=[MinValueValidator(Decimal('0'))], verbose_name='목표 금액')
    
    # 세부 목표 (선택적)
    category = models.ForeignKey(RevenueCategory, on_delete=models.CASCADE, blank=True, null=True, verbose_name='카테고리별 목표')
    assigned_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True, verbose_name='담당자별 목표')
    
    # 메타 정보
    description = models.TextField(blank=True, verbose_name='목표 설명')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, 
                                 related_name='created_targets', verbose_name='목표 설정자')
    
    class Meta:
        db_table = 'revenue_target'
        verbose_name = '매출 목표'
        verbose_name_plural = '매출 목표들'
        ordering = ['-year', '-month', '-quarter']
        unique_together = [
            ['target_type', 'year', 'month', 'category', 'assigned_user'],
            ['target_type', 'year', 'quarter', 'category', 'assigned_user'],
        ]
    
    def __str__(self):
        period = f"{self.year}년"
        if self.target_type == 'monthly' and self.month:
            period += f" {self.month}월"
        elif self.target_type == 'quarterly' and self.quarter:
            period += f" {self.quarter}분기"
        
        if self.category:
            period += f" ({self.category.name})"
        if self.assigned_user:
            period += f" - {self.assigned_user.get_full_name()}"
            
        return f"{period} 목표: {self.target_amount:,}원"
    
    def get_achievement_rate(self):
        """목표 달성률 계산"""
        from django.db.models import Sum
        from datetime import date, datetime
        
        # 기간 계산
        if self.target_type == 'monthly':
            start_date = date(self.year, self.month, 1)
            if self.month == 12:
                end_date = date(self.year + 1, 1, 1)
            else:
                end_date = date(self.year, self.month + 1, 1)
        elif self.target_type == 'quarterly':
            quarter_months = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
            start_month, end_month = quarter_months[self.quarter]
            start_date = date(self.year, start_month, 1)
            if end_month == 12:
                end_date = date(self.year + 1, 1, 1)
            else:
                end_date = date(self.year, end_month + 1, 1)
        else:  # yearly
            start_date = date(self.year, 1, 1)
            end_date = date(self.year + 1, 1, 1)
        
        # 실적 조회
        queryset = RevenueRecord.objects.filter(
            revenue_date__gte=start_date,
            revenue_date__lt=end_date,
            is_confirmed=True
        )
        
        if self.category:
            queryset = queryset.filter(category=self.category)
        if self.assigned_user:
            queryset = queryset.filter(sales_person=self.assigned_user)
        
        actual_amount = queryset.aggregate(total=Sum('net_amount'))['total'] or Decimal('0')
        
        if self.target_amount > 0:
            return float(actual_amount / self.target_amount * 100)
        return 0

class RevenueAlert(models.Model):
    """매출 알림 설정"""
    ALERT_TYPE_CHOICES = [
        ('target_achievement', '목표 달성'),
        ('overdue_payment', '연체 수금'),
        ('low_performance', '저조한 실적'),
        ('milestone_due', '마일스톤 기한'),
        ('monthly_report', '월간 리포트'),
    ]
    
    ALERT_LEVEL_CHOICES = [
        ('info', '정보'),
        ('warning', '경고'),
        ('critical', '긴급'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPE_CHOICES, verbose_name='알림 유형')
    alert_level = models.CharField(max_length=20, choices=ALERT_LEVEL_CHOICES, verbose_name='알림 레벨')
    
    # 대상
    target_users = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='revenue_alerts', verbose_name='알림 대상 사용자')
    target_roles = models.JSONField(default=list, verbose_name='알림 대상 역할')  # ['admin', 'manager', 'sales']
    
    # 조건
    threshold_value = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='임계값')
    threshold_percentage = models.FloatField(blank=True, null=True, verbose_name='임계 비율')
    
    # 알림 설정
    is_active = models.BooleanField(default=True, verbose_name='활성 상태')
    send_email = models.BooleanField(default=True, verbose_name='이메일 발송')
    send_push = models.BooleanField(default=True, verbose_name='푸시 알림')
    send_sms = models.BooleanField(default=False, verbose_name='SMS 발송')
    
    # 메시지
    title_template = models.CharField(max_length=200, verbose_name='제목 템플릿')
    message_template = models.TextField(verbose_name='메시지 템플릿')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_revenue_alerts', verbose_name='생성자')
    
    class Meta:
        db_table = 'revenue_alert'
        verbose_name = '매출 알림'
        verbose_name_plural = '매출 알림들'
        ordering = ['alert_type', '-created_at']
    
    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.get_alert_level_display()}"

class RevenueReport(models.Model):
    """매출 리포트"""
    REPORT_TYPE_CHOICES = [
        ('daily', '일간 리포트'),
        ('weekly', '주간 리포트'),
        ('monthly', '월간 리포트'),
        ('quarterly', '분기 리포트'),
        ('yearly', '연간 리포트'),
        ('custom', '커스텀 리포트'),
    ]
    
    REPORT_FORMAT_CHOICES = [
        ('html', 'HTML'),
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('json', 'JSON'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    title = models.CharField(max_length=200, verbose_name='리포트 제목')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES, verbose_name='리포트 유형')
    report_format = models.CharField(max_length=20, choices=REPORT_FORMAT_CHOICES, verbose_name='리포트 형식')
    
    # 기간
    start_date = models.DateField(verbose_name='시작일')
    end_date = models.DateField(verbose_name='종료일')
    
    # 필터 조건
    filter_conditions = models.JSONField(default=dict, verbose_name='필터 조건')
    
    # 리포트 데이터
    report_data = models.JSONField(default=dict, verbose_name='리포트 데이터')
    file_path = models.FileField(upload_to='revenue_reports/', blank=True, null=True, verbose_name='파일 경로')
    
    # 상태
    is_generated = models.BooleanField(default=False, verbose_name='생성 완료')
    generation_started_at = models.DateTimeField(blank=True, null=True, verbose_name='생성 시작 시간')
    generation_completed_at = models.DateTimeField(blank=True, null=True, verbose_name='생성 완료 시간')
    error_message = models.TextField(blank=True, verbose_name='오류 메시지')
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='생성자')
    
    class Meta:
        db_table = 'revenue_report'
        verbose_name = '매출 리포트'
        verbose_name_plural = '매출 리포트들'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.start_date} ~ {self.end_date})"
