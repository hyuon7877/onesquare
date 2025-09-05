"""
OneSquare AI 데이터 분석 시스템 - Django 모델
매출 예측, 업무 효율성 분석, 성과 분석을 위한 모델들
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from decimal import Decimal
import uuid
from datetime import datetime, date
import json

User = get_user_model()

class AIModelConfig(models.Model):
    """AI 모델 설정"""
    MODEL_TYPE_CHOICES = [
        ('linear_regression', '선형 회귀'),
        ('polynomial_regression', '다항 회귀'),
        ('moving_average', '이동 평균'),
        ('exponential_smoothing', '지수 평활법'),
        ('simple_forecast', '단순 예측'),
    ]
    
    STATUS_CHOICES = [
        ('active', '활성'),
        ('inactive', '비활성'),
        ('training', '학습 중'),
        ('error', '오류'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name='모델명')
    model_type = models.CharField(max_length=30, choices=MODEL_TYPE_CHOICES, verbose_name='모델 유형')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name='상태')
    
    # 모델 파라미터
    parameters = models.JSONField(default=dict, verbose_name='모델 파라미터')
    
    # 성능 지표
    accuracy = models.FloatField(blank=True, null=True, verbose_name='정확도')
    mae = models.FloatField(blank=True, null=True, verbose_name='평균 절대 오차')
    rmse = models.FloatField(blank=True, null=True, verbose_name='평균 제곱근 오차')
    
    # 메타 정보
    description = models.TextField(blank=True, verbose_name='설명')
    last_trained_at = models.DateTimeField(blank=True, null=True, verbose_name='마지막 학습 시간')
    training_data_size = models.IntegerField(default=0, verbose_name='학습 데이터 크기')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='생성자')
    
    class Meta:
        db_table = 'ai_model_config'
        verbose_name = 'AI 모델 설정'
        verbose_name_plural = 'AI 모델 설정들'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_model_type_display()})"

class RevenuePrediction(models.Model):
    """매출 예측"""
    PREDICTION_TYPE_CHOICES = [
        ('monthly', '월별 예측'),
        ('quarterly', '분기별 예측'),
        ('yearly', '연간 예측'),
        ('project', '프로젝트별 예측'),
    ]
    
    CONFIDENCE_LEVEL_CHOICES = [
        ('high', '높음 (90% 이상)'),
        ('medium', '보통 (70-90%)'),
        ('low', '낮음 (70% 미만)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model = models.ForeignKey(AIModelConfig, on_delete=models.CASCADE, verbose_name='사용된 모델')
    
    # 예측 정보
    prediction_type = models.CharField(max_length=20, choices=PREDICTION_TYPE_CHOICES, verbose_name='예측 유형')
    prediction_date = models.DateField(verbose_name='예측 기준일')
    target_period_start = models.DateField(verbose_name='예측 기간 시작')
    target_period_end = models.DateField(verbose_name='예측 기간 종료')
    
    # 예측 결과
    predicted_amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name='예측 매출액')
    confidence_score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)], verbose_name='신뢰도 점수')
    confidence_level = models.CharField(max_length=20, choices=CONFIDENCE_LEVEL_CHOICES, verbose_name='신뢰도 수준')
    
    # 예측 범위 (신뢰구간)
    lower_bound = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='하한선')
    upper_bound = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='상한선')
    
    # 실제 결과 (예측 검증용)
    actual_amount = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='실제 매출액')
    prediction_error = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='예측 오차')
    
    # 예측 근거
    factors_considered = models.JSONField(default=list, verbose_name='고려된 요인들')
    trend_analysis = models.TextField(blank=True, verbose_name='트렌드 분석')
    
    # 메타 정보
    notes = models.TextField(blank=True, verbose_name='메모')
    is_validated = models.BooleanField(default=False, verbose_name='검증 완료')
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='생성자')
    
    class Meta:
        db_table = 'revenue_prediction'
        verbose_name = '매출 예측'
        verbose_name_plural = '매출 예측들'
        ordering = ['-prediction_date', '-created_at']
        indexes = [
            models.Index(fields=['prediction_date']),
            models.Index(fields=['target_period_start', 'target_period_end']),
            models.Index(fields=['confidence_level']),
        ]
    
    def __str__(self):
        return f"{self.get_prediction_type_display()} - {self.predicted_amount:,}원 ({self.target_period_start}~{self.target_period_end})"
    
    def calculate_accuracy(self):
        """예측 정확도 계산"""
        if self.actual_amount is None or self.predicted_amount == 0:
            return None
        
        error_rate = abs(self.actual_amount - self.predicted_amount) / self.predicted_amount * 100
        accuracy = max(0, 100 - error_rate)
        return round(accuracy, 2)
    
    def save(self, *args, **kwargs):
        # 예측 오차 자동 계산
        if self.actual_amount is not None and self.predicted_amount:
            self.prediction_error = self.actual_amount - self.predicted_amount
        
        # 신뢰도 수준 자동 설정
        if self.confidence_score >= 90:
            self.confidence_level = 'high'
        elif self.confidence_score >= 70:
            self.confidence_level = 'medium'
        else:
            self.confidence_level = 'low'
        
        super().save(*args, **kwargs)

class WorkEfficiencyAnalysis(models.Model):
    """업무 효율성 분석"""
    ANALYSIS_TYPE_CHOICES = [
        ('individual', '개인별 분석'),
        ('team', '팀별 분석'),
        ('project', '프로젝트별 분석'),
        ('department', '부서별 분석'),
    ]
    
    EFFICIENCY_LEVEL_CHOICES = [
        ('excellent', '우수 (90% 이상)'),
        ('good', '양호 (70-90%)'),
        ('average', '보통 (50-70%)'),
        ('below_average', '미흡 (50% 미만)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 분석 대상
    analysis_type = models.CharField(max_length=20, choices=ANALYSIS_TYPE_CHOICES, verbose_name='분석 유형')
    target_user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, 
                                   related_name='efficiency_analyses', verbose_name='대상 사용자')
    target_project = models.ForeignKey('revenue.Project', on_delete=models.CASCADE, blank=True, null=True, verbose_name='대상 프로젝트')
    
    # 분석 기간
    analysis_period_start = models.DateField(verbose_name='분석 기간 시작')
    analysis_period_end = models.DateField(verbose_name='분석 기간 종료')
    
    # 효율성 지표
    efficiency_score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)], verbose_name='효율성 점수')
    efficiency_level = models.CharField(max_length=20, choices=EFFICIENCY_LEVEL_CHOICES, verbose_name='효율성 수준')
    
    # 세부 지표
    task_completion_rate = models.FloatField(blank=True, null=True, verbose_name='업무 완료율')
    average_task_duration = models.FloatField(blank=True, null=True, verbose_name='평균 업무 소요 시간')
    quality_score = models.FloatField(blank=True, null=True, verbose_name='품질 점수')
    productivity_index = models.FloatField(blank=True, null=True, verbose_name='생산성 지수')
    
    # 시간 분석
    total_work_hours = models.FloatField(blank=True, null=True, verbose_name='총 근무 시간')
    productive_hours = models.FloatField(blank=True, null=True, verbose_name='생산적 근무 시간')
    overtime_hours = models.FloatField(blank=True, null=True, verbose_name='초과 근무 시간')
    
    # 분석 결과
    strengths = models.JSONField(default=list, verbose_name='강점 영역')
    weaknesses = models.JSONField(default=list, verbose_name='개선 필요 영역')
    recommendations = models.JSONField(default=list, verbose_name='개선 권고사항')
    
    # 비교 분석
    comparison_data = models.JSONField(default=dict, verbose_name='비교 데이터')
    trend_analysis = models.TextField(blank=True, verbose_name='트렌드 분석')
    
    created_at = models.DateTimeField(auto_now_add=True)
    analyzed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='conducted_analyses', verbose_name='분석자')
    
    class Meta:
        db_table = 'work_efficiency_analysis'
        verbose_name = '업무 효율성 분석'
        verbose_name_plural = '업무 효율성 분석들'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['analysis_period_start', 'analysis_period_end']),
            models.Index(fields=['efficiency_level']),
            models.Index(fields=['target_user', 'created_at']),
        ]
    
    def __str__(self):
        target = "전체"
        if self.target_user:
            target = self.target_user.get_full_name()
        elif self.target_project:
            target = self.target_project.name
        
        return f"{self.get_analysis_type_display()} - {target} ({self.efficiency_score:.1f}점)"
    
    def save(self, *args, **kwargs):
        # 효율성 수준 자동 설정
        if self.efficiency_score >= 90:
            self.efficiency_level = 'excellent'
        elif self.efficiency_score >= 70:
            self.efficiency_level = 'good'
        elif self.efficiency_score >= 50:
            self.efficiency_level = 'average'
        else:
            self.efficiency_level = 'below_average'
        
        super().save(*args, **kwargs)

class PerformanceAnalysis(models.Model):
    """성과 분석"""
    PERFORMANCE_TYPE_CHOICES = [
        ('sales', '영업 성과'),
        ('project', '프로젝트 성과'),
        ('team', '팀 성과'),
        ('financial', '재무 성과'),
        ('operational', '운영 성과'),
    ]
    
    PERFORMANCE_GRADE_CHOICES = [
        ('A+', 'A+ (95점 이상)'),
        ('A', 'A (90-94점)'),
        ('B+', 'B+ (85-89점)'),
        ('B', 'B (80-84점)'),
        ('C+', 'C+ (75-79점)'),
        ('C', 'C (70-74점)'),
        ('D', 'D (70점 미만)'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 성과 분석 기본 정보
    performance_type = models.CharField(max_length=20, choices=PERFORMANCE_TYPE_CHOICES, verbose_name='성과 유형')
    title = models.CharField(max_length=200, verbose_name='성과 분석 제목')
    
    # 분석 대상
    target_user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, verbose_name='대상 사용자')
    target_project = models.ForeignKey('revenue.Project', on_delete=models.CASCADE, blank=True, null=True, verbose_name='대상 프로젝트')
    
    # 분석 기간
    analysis_period_start = models.DateField(verbose_name='분석 기간 시작')
    analysis_period_end = models.DateField(verbose_name='분석 기간 종료')
    
    # 성과 점수
    overall_score = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)], verbose_name='종합 점수')
    performance_grade = models.CharField(max_length=5, choices=PERFORMANCE_GRADE_CHOICES, verbose_name='성과 등급')
    
    # 세부 성과 지표
    kpi_scores = models.JSONField(default=dict, verbose_name='KPI 점수들')
    target_achievement_rate = models.FloatField(blank=True, null=True, verbose_name='목표 달성률')
    
    # 정량적 지표
    revenue_generated = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='창출 매출')
    cost_saved = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='절약 비용')
    roi = models.FloatField(blank=True, null=True, verbose_name='투자 수익률')
    
    # 정성적 평가
    qualitative_assessment = models.TextField(blank=True, verbose_name='정성적 평가')
    achievements = models.JSONField(default=list, verbose_name='주요 성과')
    challenges = models.JSONField(default=list, verbose_name='도전 과제')
    
    # 개선 사항
    improvement_areas = models.JSONField(default=list, verbose_name='개선 영역')
    action_plans = models.JSONField(default=list, verbose_name='실행 계획')
    next_period_goals = models.JSONField(default=list, verbose_name='다음 기간 목표')
    
    # 비교 분석
    previous_period_score = models.FloatField(blank=True, null=True, verbose_name='이전 기간 점수')
    score_change = models.FloatField(blank=True, null=True, verbose_name='점수 변화')
    peer_comparison = models.JSONField(default=dict, verbose_name='동료 비교')
    
    # 메타 정보
    analysis_methodology = models.TextField(blank=True, verbose_name='분석 방법론')
    data_sources = models.JSONField(default=list, verbose_name='데이터 소스')
    
    created_at = models.DateTimeField(auto_now_add=True)
    analyzed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='conducted_performance_analyses', verbose_name='분석자')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='reviewed_performance_analyses', verbose_name='검토자')
    
    class Meta:
        db_table = 'performance_analysis'
        verbose_name = '성과 분석'
        verbose_name_plural = '성과 분석들'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['performance_type', 'created_at']),
            models.Index(fields=['target_user', 'analysis_period_start']),
            models.Index(fields=['overall_score']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.performance_grade} ({self.overall_score:.1f}점)"
    
    def save(self, *args, **kwargs):
        # 성과 등급 자동 설정
        if self.overall_score >= 95:
            self.performance_grade = 'A+'
        elif self.overall_score >= 90:
            self.performance_grade = 'A'
        elif self.overall_score >= 85:
            self.performance_grade = 'B+'
        elif self.overall_score >= 80:
            self.performance_grade = 'B'
        elif self.overall_score >= 75:
            self.performance_grade = 'C+'
        elif self.overall_score >= 70:
            self.performance_grade = 'C'
        else:
            self.performance_grade = 'D'
        
        # 점수 변화 계산
        if self.previous_period_score is not None:
            self.score_change = self.overall_score - self.previous_period_score
        
        super().save(*args, **kwargs)

class AnomalyDetection(models.Model):
    """이상 패턴 감지"""
    ANOMALY_TYPE_CHOICES = [
        ('revenue_drop', '매출 급감'),
        ('revenue_spike', '매출 급증'),
        ('efficiency_drop', '효율성 저하'),
        ('cost_increase', '비용 급증'),
        ('pattern_change', '패턴 변화'),
        ('performance_issue', '성과 이슈'),
    ]
    
    SEVERITY_CHOICES = [
        ('low', '낮음'),
        ('medium', '보통'),
        ('high', '높음'),
        ('critical', '긴급'),
    ]
    
    STATUS_CHOICES = [
        ('detected', '감지됨'),
        ('investigating', '조사 중'),
        ('resolved', '해결됨'),
        ('ignored', '무시됨'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 이상 감지 정보
    anomaly_type = models.CharField(max_length=30, choices=ANOMALY_TYPE_CHOICES, verbose_name='이상 유형')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, verbose_name='심각도')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='detected', verbose_name='상태')
    
    # 감지 상세 정보
    detected_at = models.DateTimeField(auto_now_add=True, verbose_name='감지 시간')
    data_source = models.CharField(max_length=100, verbose_name='데이터 소스')
    affected_metric = models.CharField(max_length=100, verbose_name='영향받은 지표')
    
    # 이상값 정보
    expected_value = models.FloatField(blank=True, null=True, verbose_name='예상값')
    actual_value = models.FloatField(blank=True, null=True, verbose_name='실제값')
    deviation_percentage = models.FloatField(blank=True, null=True, verbose_name='편차율')
    
    # 관련 정보
    related_user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True, verbose_name='관련 사용자')
    related_project = models.ForeignKey('revenue.Project', on_delete=models.CASCADE, blank=True, null=True, verbose_name='관련 프로젝트')
    
    # 분석 결과
    description = models.TextField(verbose_name='이상 상황 설명')
    possible_causes = models.JSONField(default=list, verbose_name='가능한 원인들')
    impact_assessment = models.TextField(blank=True, verbose_name='영향 평가')
    recommended_actions = models.JSONField(default=list, verbose_name='권장 조치사항')
    
    # 대응 정보
    investigated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                       related_name='investigated_anomalies', verbose_name='조사자')
    resolution_notes = models.TextField(blank=True, verbose_name='해결 노트')
    resolved_at = models.DateTimeField(blank=True, null=True, verbose_name='해결 시간')
    
    # 알림 설정
    alert_sent = models.BooleanField(default=False, verbose_name='알림 발송 여부')
    alert_recipients = models.JSONField(default=list, verbose_name='알림 수신자들')
    
    class Meta:
        db_table = 'anomaly_detection'
        verbose_name = '이상 패턴 감지'
        verbose_name_plural = '이상 패턴 감지들'
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['anomaly_type', 'severity']),
            models.Index(fields=['status', 'detected_at']),
            models.Index(fields=['related_user', 'detected_at']),
        ]
    
    def __str__(self):
        return f"{self.get_anomaly_type_display()} - {self.get_severity_display()} ({self.detected_at.strftime('%Y-%m-%d %H:%M')})"

class AIInsight(models.Model):
    """AI 인사이트"""
    INSIGHT_TYPE_CHOICES = [
        ('trend', '트렌드 분석'),
        ('prediction', '예측 분석'),
        ('opportunity', '기회 발견'),
        ('risk', '리스크 분석'),
        ('optimization', '최적화 제안'),
        ('benchmark', '벤치마킹'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', '낮음'),
        ('medium', '보통'),
        ('high', '높음'),
        ('urgent', '긴급'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # 인사이트 기본 정보
    insight_type = models.CharField(max_length=20, choices=INSIGHT_TYPE_CHOICES, verbose_name='인사이트 유형')
    title = models.CharField(max_length=200, verbose_name='제목')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, verbose_name='우선순위')
    
    # 인사이트 내용
    summary = models.TextField(verbose_name='요약')
    detailed_analysis = models.TextField(verbose_name='상세 분석')
    key_findings = models.JSONField(default=list, verbose_name='주요 발견사항')
    supporting_data = models.JSONField(default=dict, verbose_name='뒷받침 데이터')
    
    # 실행 가능한 권고사항
    actionable_recommendations = models.JSONField(default=list, verbose_name='실행 가능한 권고사항')
    expected_impact = models.TextField(blank=True, verbose_name='예상 효과')
    implementation_steps = models.JSONField(default=list, verbose_name='구현 단계')
    
    # 관련 정보
    related_models = models.JSONField(default=list, verbose_name='관련 모델들')
    data_confidence = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(100)], 
                                       verbose_name='데이터 신뢰도')
    
    # 대상 정보
    target_audience = models.JSONField(default=list, verbose_name='대상 독자')
    affected_areas = models.JSONField(default=list, verbose_name='영향 영역')
    
    # 상태 정보
    is_active = models.BooleanField(default=True, verbose_name='활성 상태')
    is_read = models.BooleanField(default=False, verbose_name='읽음 상태')
    is_implemented = models.BooleanField(default=False, verbose_name='구현 상태')
    
    # 피드백
    feedback_score = models.FloatField(blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(5)], 
                                      verbose_name='피드백 점수')
    feedback_comments = models.TextField(blank=True, verbose_name='피드백 댓글')
    
    created_at = models.DateTimeField(auto_now_add=True)
    generated_by_model = models.ForeignKey(AIModelConfig, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='생성 모델')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='검토자')
    
    class Meta:
        db_table = 'ai_insight'
        verbose_name = 'AI 인사이트'
        verbose_name_plural = 'AI 인사이트들'
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['insight_type', 'priority']),
            models.Index(fields=['is_active', 'created_at']),
            models.Index(fields=['data_confidence']),
        ]
    
    def __str__(self):
        return f"{self.get_insight_type_display()} - {self.title}"
