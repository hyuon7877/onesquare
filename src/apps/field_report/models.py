"""
OneSquare 현장 리포트 시스템 모델

파트너 전용 현장 작업 관리 및 리포트 기능
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class FieldSite(models.Model):
    """현장 정보"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name='현장명')
    address = models.TextField(verbose_name='주소')
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True, verbose_name='위도')
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True, verbose_name='경도')
    description = models.TextField(blank=True, verbose_name='현장 설명')
    
    # Notion 연동
    notion_page_id = models.CharField(max_length=100, blank=True, verbose_name='Notion 페이지 ID')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, verbose_name='활성 상태')
    
    class Meta:
        verbose_name = '현장'
        verbose_name_plural = '현장 목록'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class WorkSession(models.Model):
    """업무 세션 (출근/퇴근 기록)"""
    WORK_STATUS_CHOICES = [
        ('started', '업무 시작'),
        ('paused', '일시 중지'),
        ('resumed', '재개'),
        ('completed', '업무 완료'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='작업자')
    site = models.ForeignKey(FieldSite, on_delete=models.CASCADE, verbose_name='현장')
    
    start_time = models.DateTimeField(verbose_name='시작 시간')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='종료 시간')
    status = models.CharField(max_length=20, choices=WORK_STATUS_CHOICES, default='started', verbose_name='상태')
    
    # GPS 위치 정보
    start_latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True, verbose_name='시작 위치 위도')
    start_longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True, verbose_name='시작 위치 경도')
    end_latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True, verbose_name='종료 위치 위도')
    end_longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True, verbose_name='종료 위치 경도')
    
    # 위치 검증
    location_verified = models.BooleanField(default=False, verbose_name='위치 검증 완료')
    location_accuracy = models.FloatField(null=True, blank=True, verbose_name='GPS 정확도 (미터)')
    
    notes = models.TextField(blank=True, verbose_name='메모')
    
    # Notion 연동
    notion_page_id = models.CharField(max_length=100, blank=True, verbose_name='Notion 페이지 ID')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '업무 세션'
        verbose_name_plural = '업무 세션 목록'
        ordering = ['-start_time']
    
    def __str__(self):
        return f"{self.user.username} - {self.site.name} ({self.start_time.strftime('%Y-%m-%d %H:%M')})"
    
    @property
    def duration(self):
        """업무 시간 계산"""
        if self.end_time:
            return self.end_time - self.start_time
        return timezone.now() - self.start_time
    
    @property
    def duration_hours(self):
        """업무 시간을 시간 단위로 반환"""
        duration = self.duration
        return duration.total_seconds() / 3600 if duration else 0


class TaskChecklist(models.Model):
    """작업 체크리스트 템플릿"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name='체크리스트명')
    site = models.ForeignKey(FieldSite, on_delete=models.CASCADE, null=True, blank=True, verbose_name='전용 현장')
    description = models.TextField(blank=True, verbose_name='설명')
    
    # JSON 필드로 체크리스트 아이템 저장
    checklist_items = models.JSONField(default=list, verbose_name='체크리스트 항목')
    
    # 우선순위
    priority = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='우선순위 (1-5)'
    )
    
    is_active = models.BooleanField(default=True, verbose_name='활성 상태')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '작업 체크리스트'
        verbose_name_plural = '작업 체크리스트 목록'
        ordering = ['priority', '-created_at']
    
    def __str__(self):
        return self.name


class WorkReport(models.Model):
    """현장 작업 리포트"""
    REPORT_STATUS_CHOICES = [
        ('draft', '임시저장'),
        ('submitted', '제출완료'),
        ('reviewed', '검토완료'),
        ('approved', '승인완료'),
        ('rejected', '반려'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(WorkSession, on_delete=models.CASCADE, verbose_name='업무 세션')
    checklist = models.ForeignKey(TaskChecklist, on_delete=models.CASCADE, verbose_name='사용한 체크리스트')
    
    title = models.CharField(max_length=200, verbose_name='리포트 제목')
    status = models.CharField(max_length=20, choices=REPORT_STATUS_CHOICES, default='draft', verbose_name='상태')
    
    # 체크리스트 완료 상태 (JSON)
    checklist_status = models.JSONField(default=dict, verbose_name='체크리스트 완료 상태')
    
    # 진행률
    completion_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='완료율 (%)'
    )
    
    # 추가 메모
    additional_notes = models.TextField(blank=True, verbose_name='추가 메모')
    
    # 관리자 검토
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reviewed_reports',
        verbose_name='검토자'
    )
    review_notes = models.TextField(blank=True, verbose_name='검토 의견')
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='검토 일시')
    
    # Notion 연동
    notion_page_id = models.CharField(max_length=100, blank=True, verbose_name='Notion 페이지 ID')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '현장 작업 리포트'
        verbose_name_plural = '현장 작업 리포트 목록'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.session.user.username}"
    
    def update_completion_percentage(self):
        """체크리스트 완료율 자동 계산"""
        if not self.checklist_status or not self.checklist.checklist_items:
            self.completion_percentage = 0
            return
        
        total_items = len(self.checklist.checklist_items)
        completed_items = sum(1 for item_id, status in self.checklist_status.items() if status.get('completed', False))
        
        self.completion_percentage = int((completed_items / total_items) * 100) if total_items > 0 else 0


class ReportPhoto(models.Model):
    """리포트 첨부 사진"""
    PHOTO_TYPE_CHOICES = [
        ('before', '작업 전'),
        ('during', '작업 중'),
        ('after', '작업 후'),
        ('issue', '문제점'),
        ('equipment', '장비'),
        ('material', '자재'),
        ('other', '기타'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(WorkReport, on_delete=models.CASCADE, related_name='photos', verbose_name='리포트')
    
    # 사진 파일
    original_image = models.ImageField(upload_to='field_reports/photos/original/', verbose_name='원본 이미지')
    compressed_image = models.ImageField(upload_to='field_reports/photos/compressed/', null=True, blank=True, verbose_name='압축 이미지')
    thumbnail = models.ImageField(upload_to='field_reports/photos/thumbnails/', null=True, blank=True, verbose_name='썸네일')
    
    # 메타데이터
    photo_type = models.CharField(max_length=20, choices=PHOTO_TYPE_CHOICES, default='other', verbose_name='사진 유형')
    caption = models.CharField(max_length=500, blank=True, verbose_name='사진 설명')
    
    # EXIF 데이터에서 추출된 위치 정보
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True, verbose_name='위도')
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True, verbose_name='경도')
    taken_at = models.DateTimeField(null=True, blank=True, verbose_name='촬영 시간')
    
    # 파일 정보
    original_file_size = models.BigIntegerField(null=True, blank=True, verbose_name='원본 파일 크기 (bytes)')
    compressed_file_size = models.BigIntegerField(null=True, blank=True, verbose_name='압축 파일 크기 (bytes)')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = '리포트 사진'
        verbose_name_plural = '리포트 사진 목록'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.report.title} - {self.get_photo_type_display()}"
    
    @property
    def compression_ratio(self):
        """압축률 계산"""
        if self.original_file_size and self.compressed_file_size:
            return round((1 - self.compressed_file_size / self.original_file_size) * 100, 2)
        return 0


class InventoryItem(models.Model):
    """비품 재고 항목"""
    ITEM_CATEGORY_CHOICES = [
        ('tool', '공구'),
        ('material', '자재'),
        ('equipment', '장비'),
        ('safety', '안전용품'),
        ('consumable', '소모품'),
        ('other', '기타'),
    ]
    
    UNIT_CHOICES = [
        ('ea', '개'),
        ('kg', 'kg'),
        ('m', 'm'),
        ('box', '박스'),
        ('roll', '롤'),
        ('bottle', '병'),
        ('pack', '팩'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name='품목명')
    code = models.CharField(max_length=50, unique=True, verbose_name='품목 코드')
    category = models.CharField(max_length=20, choices=ITEM_CATEGORY_CHOICES, verbose_name='카테고리')
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, verbose_name='단위')
    
    description = models.TextField(blank=True, verbose_name='설명')
    
    # 재고 관리 기준
    minimum_stock = models.IntegerField(default=0, verbose_name='최소 재고량')
    maximum_stock = models.IntegerField(default=1000, verbose_name='최대 재고량')
    
    is_active = models.BooleanField(default=True, verbose_name='활성 상태')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '비품 항목'
        verbose_name_plural = '비품 항목 목록'
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class InventoryCheck(models.Model):
    """현장 비품 재고 체크"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(WorkReport, on_delete=models.CASCADE, related_name='inventory_checks', verbose_name='리포트')
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, verbose_name='비품 항목')
    
    # 재고 수량
    current_quantity = models.IntegerField(verbose_name='현재 수량')
    required_quantity = models.IntegerField(null=True, blank=True, verbose_name='필요 수량')
    
    # 상태
    is_sufficient = models.BooleanField(verbose_name='재고 충분')
    needs_replenishment = models.BooleanField(default=False, verbose_name='보충 필요')
    
    notes = models.TextField(blank=True, verbose_name='비고')
    checked_at = models.DateTimeField(auto_now_add=True, verbose_name='체크 일시')
    
    class Meta:
        verbose_name = '재고 체크'
        verbose_name_plural = '재고 체크 목록'
        unique_together = [['report', 'item']]
        ordering = ['-checked_at']
    
    def __str__(self):
        return f"{self.item.name} - {self.current_quantity}{self.item.unit}"
    
    def save(self, *args, **kwargs):
        """재고 부족 여부 자동 판단"""
        if self.current_quantity < self.item.minimum_stock:
            self.is_sufficient = False
            self.needs_replenishment = True
        else:
            self.is_sufficient = True
            self.needs_replenishment = False
        
        super().save(*args, **kwargs)