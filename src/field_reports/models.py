from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json


class FieldReport(models.Model):
    """현장 리포트 모델"""
    
    STATUS_CHOICES = [
        ('draft', '임시저장'),
        ('submitted', '제출완료'),
        ('synced', '동기화완료'),
        ('approved', '승인됨'),
        ('rejected', '반려됨'),
    ]
    
    REPORT_TYPE_CHOICES = [
        ('daily', '일일보고'),
        ('incident', '사고/이슈'),
        ('inspection', '점검보고'),
        ('progress', '진행상황'),
        ('completion', '완료보고'),
        ('other', '기타'),
    ]
    
    # 기본 정보
    title = models.CharField(max_length=200, verbose_name='제목')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES, default='daily', verbose_name='보고 유형')
    content = models.TextField(verbose_name='내용')
    
    # 작성자 정보
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='field_reports', verbose_name='작성자')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='작성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name='제출일시')
    
    # 프로젝트/현장 정보
    project_name = models.CharField(max_length=100, verbose_name='프로젝트명')
    site_name = models.CharField(max_length=100, verbose_name='현장명')
    contractor = models.CharField(max_length=100, blank=True, verbose_name='도급사')
    
    # 위치 정보
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True, verbose_name='위도')
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True, verbose_name='경도')
    location_address = models.CharField(max_length=255, blank=True, verbose_name='주소')
    
    # 상태 관리
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name='상태')
    is_offline = models.BooleanField(default=False, verbose_name='오프라인 작성')
    sync_status = models.CharField(max_length=50, blank=True, verbose_name='동기화 상태')
    
    # 날씨 정보 (선택사항)
    weather = models.CharField(max_length=50, blank=True, verbose_name='날씨')
    temperature = models.CharField(max_length=20, blank=True, verbose_name='온도')
    
    # 참석자/작업자
    workers_count = models.IntegerField(default=0, verbose_name='작업인원')
    attendees = models.TextField(blank=True, verbose_name='참석자 명단')
    
    # 승인 관련
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, 
                                   related_name='reviewed_reports', verbose_name='검토자')
    review_comment = models.TextField(blank=True, verbose_name='검토 의견')
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='검토일시')
    
    # Notion 동기화
    notion_page_id = models.CharField(max_length=100, blank=True, verbose_name='Notion 페이지 ID')
    notion_sync_at = models.DateTimeField(null=True, blank=True, verbose_name='Notion 동기화 시간')
    
    # 메타데이터 (추가 정보를 JSON으로 저장)
    metadata = models.JSONField(default=dict, blank=True, verbose_name='추가 데이터')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = '현장 리포트'
        verbose_name_plural = '현장 리포트'
        
    def __str__(self):
        return f"[{self.get_report_type_display()}] {self.title} - {self.author.username}"
    
    def save(self, *args, **kwargs):
        if self.status == 'submitted' and not self.submitted_at:
            self.submitted_at = timezone.now()
        super().save(*args, **kwargs)


class ReportAttachment(models.Model):
    """리포트 첨부파일"""
    
    FILE_TYPE_CHOICES = [
        ('image', '이미지'),
        ('document', '문서'),
        ('video', '동영상'),
        ('audio', '음성'),
        ('other', '기타'),
    ]
    
    report = models.ForeignKey(FieldReport, on_delete=models.CASCADE, 
                              related_name='attachments', verbose_name='리포트')
    file = models.FileField(upload_to='field_reports/%Y/%m/%d/', verbose_name='파일')
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES, default='image', verbose_name='파일 유형')
    file_name = models.CharField(max_length=255, verbose_name='파일명')
    file_size = models.IntegerField(default=0, verbose_name='파일 크기')
    
    # 이미지인 경우 썸네일
    thumbnail = models.ImageField(upload_to='field_reports/thumbnails/%Y/%m/%d/', 
                                 null=True, blank=True, verbose_name='썸네일')
    
    # 설명
    description = models.CharField(max_length=255, blank=True, verbose_name='설명')
    
    # 업로드 정보
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='업로드 시간')
    is_synced = models.BooleanField(default=False, verbose_name='동기화 여부')
    
    # EXIF 데이터 (이미지인 경우)
    exif_data = models.JSONField(default=dict, blank=True, verbose_name='EXIF 데이터')
    
    class Meta:
        ordering = ['uploaded_at']
        verbose_name = '첨부파일'
        verbose_name_plural = '첨부파일'
    
    def __str__(self):
        return f"{self.file_name} ({self.get_file_type_display()})"
