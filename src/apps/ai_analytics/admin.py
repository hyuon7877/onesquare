"""
AI Analytics Admin 설정
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import (
    AIModelConfig, RevenuePrediction, WorkEfficiencyAnalysis, 
    PerformanceAnalysis, AnomalyDetection, AIInsight
)

@admin.register(AIModelConfig)
class AIModelConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'model_type', 'status', 'accuracy', 'last_trained_at', 'created_at']
    list_filter = ['model_type', 'status', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('name', 'model_type', 'status', 'description')
        }),
        ('성능 지표', {
            'fields': ('accuracy', 'mae', 'rmse', 'training_data_size', 'last_trained_at')
        }),
        ('설정', {
            'fields': ('parameters',),
            'classes': ('collapse',)
        }),
        ('메타 정보', {
            'fields': ('id', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(RevenuePrediction)
class RevenuePredictionAdmin(admin.ModelAdmin):
    list_display = ['prediction_type', 'predicted_amount', 'confidence_level', 'target_period', 'is_validated', 'created_at']
    list_filter = ['prediction_type', 'confidence_level', 'is_validated', 'created_at']
    search_fields = ['trend_analysis', 'notes']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'
    
    def target_period(self, obj):
        return f"{obj.target_period_start} ~ {obj.target_period_end}"
    target_period.short_description = '예측 기간'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('model', 'created_by')
    
    fieldsets = (
        ('예측 정보', {
            'fields': ('model', 'prediction_type', 'prediction_date', 'target_period_start', 'target_period_end')
        }),
        ('예측 결과', {
            'fields': ('predicted_amount', 'confidence_score', 'confidence_level', 'lower_bound', 'upper_bound')
        }),
        ('검증 결과', {
            'fields': ('actual_amount', 'prediction_error', 'is_validated'),
            'classes': ('collapse',)
        }),
        ('분석 내용', {
            'fields': ('factors_considered', 'trend_analysis', 'notes'),
            'classes': ('collapse',)
        }),
        ('메타 정보', {
            'fields': ('id', 'created_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(WorkEfficiencyAnalysis)
class WorkEfficiencyAnalysisAdmin(admin.ModelAdmin):
    list_display = ['analysis_type', 'target_display', 'efficiency_score', 'efficiency_level', 'analysis_period', 'created_at']
    list_filter = ['analysis_type', 'efficiency_level', 'created_at']
    search_fields = ['target_user__username', 'target_project__name']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'
    
    def target_display(self, obj):
        if obj.target_user:
            return obj.target_user.get_full_name()
        elif obj.target_project:
            return obj.target_project.name
        return "전체"
    target_display.short_description = '분석 대상'
    
    def analysis_period(self, obj):
        return f"{obj.analysis_period_start} ~ {obj.analysis_period_end}"
    analysis_period.short_description = '분석 기간'
    
    fieldsets = (
        ('분석 기본 정보', {
            'fields': ('analysis_type', 'target_user', 'target_project', 'analysis_period_start', 'analysis_period_end')
        }),
        ('효율성 지표', {
            'fields': ('efficiency_score', 'efficiency_level', 'task_completion_rate', 'average_task_duration', 'quality_score', 'productivity_index')
        }),
        ('시간 분석', {
            'fields': ('total_work_hours', 'productive_hours', 'overtime_hours'),
            'classes': ('collapse',)
        }),
        ('분석 결과', {
            'fields': ('strengths', 'weaknesses', 'recommendations', 'comparison_data', 'trend_analysis'),
            'classes': ('collapse',)
        }),
        ('메타 정보', {
            'fields': ('id', 'analyzed_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(PerformanceAnalysis)
class PerformanceAnalysisAdmin(admin.ModelAdmin):
    list_display = ['title', 'performance_type', 'overall_score', 'performance_grade', 'target_display', 'created_at']
    list_filter = ['performance_type', 'performance_grade', 'created_at']
    search_fields = ['title', 'target_user__username', 'target_project__name']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'
    
    def target_display(self, obj):
        if obj.target_user:
            return obj.target_user.get_full_name()
        elif obj.target_project:
            return obj.target_project.name
        return "전체"
    target_display.short_description = '분석 대상'
    
    fieldsets = (
        ('성과 분석 기본 정보', {
            'fields': ('performance_type', 'title', 'target_user', 'target_project', 'analysis_period_start', 'analysis_period_end')
        }),
        ('성과 점수', {
            'fields': ('overall_score', 'performance_grade', 'kpi_scores', 'target_achievement_rate')
        }),
        ('정량적 지표', {
            'fields': ('revenue_generated', 'cost_saved', 'roi'),
            'classes': ('collapse',)
        }),
        ('정성적 평가', {
            'fields': ('qualitative_assessment', 'achievements', 'challenges'),
            'classes': ('collapse',)
        }),
        ('개선 사항', {
            'fields': ('improvement_areas', 'action_plans', 'next_period_goals'),
            'classes': ('collapse',)
        }),
        ('비교 분석', {
            'fields': ('previous_period_score', 'score_change', 'peer_comparison'),
            'classes': ('collapse',)
        }),
        ('메타 정보', {
            'fields': ('analysis_methodology', 'data_sources', 'id', 'analyzed_by', 'reviewed_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(AnomalyDetection)
class AnomalyDetectionAdmin(admin.ModelAdmin):
    list_display = ['anomaly_type', 'severity', 'status', 'affected_metric', 'deviation_display', 'detected_at']
    list_filter = ['anomaly_type', 'severity', 'status', 'detected_at']
    search_fields = ['description', 'data_source', 'affected_metric']
    readonly_fields = ['id', 'detected_at']
    date_hierarchy = 'detected_at'
    actions = ['mark_as_investigating', 'mark_as_resolved', 'mark_as_ignored']
    
    def deviation_display(self, obj):
        if obj.deviation_percentage:
            color = 'red' if obj.severity in ['high', 'critical'] else 'orange'
            return format_html(
                '<span style="color: {};">{:.1f}%</span>',
                color, obj.deviation_percentage
            )
        return '-'
    deviation_display.short_description = '편차율'
    
    def mark_as_investigating(self, request, queryset):
        updated = queryset.update(status='investigating', investigated_by=request.user)
        self.message_user(request, f'{updated}개의 이상 패턴을 조사 중으로 변경했습니다.')
    mark_as_investigating.short_description = '선택된 항목을 조사 중으로 표시'
    
    def mark_as_resolved(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status='resolved', resolved_at=timezone.now(), investigated_by=request.user)
        self.message_user(request, f'{updated}개의 이상 패턴을 해결됨으로 변경했습니다.')
    mark_as_resolved.short_description = '선택된 항목을 해결됨으로 표시'
    
    def mark_as_ignored(self, request, queryset):
        updated = queryset.update(status='ignored')
        self.message_user(request, f'{updated}개의 이상 패턴을 무시됨으로 변경했습니다.')
    mark_as_ignored.short_description = '선택된 항목을 무시됨으로 표시'
    
    fieldsets = (
        ('이상 감지 정보', {
            'fields': ('anomaly_type', 'severity', 'status', 'data_source', 'affected_metric')
        }),
        ('이상값 정보', {
            'fields': ('expected_value', 'actual_value', 'deviation_percentage')
        }),
        ('관련 정보', {
            'fields': ('related_user', 'related_project'),
            'classes': ('collapse',)
        }),
        ('분석 결과', {
            'fields': ('description', 'possible_causes', 'impact_assessment', 'recommended_actions'),
            'classes': ('collapse',)
        }),
        ('대응 정보', {
            'fields': ('investigated_by', 'resolution_notes', 'resolved_at'),
            'classes': ('collapse',)
        }),
        ('알림 정보', {
            'fields': ('alert_sent', 'alert_recipients'),
            'classes': ('collapse',)
        }),
        ('메타 정보', {
            'fields': ('id', 'detected_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(AIInsight)
class AIInsightAdmin(admin.ModelAdmin):
    list_display = ['insight_type', 'title', 'priority', 'data_confidence', 'is_active', 'is_read', 'is_implemented', 'created_at']
    list_filter = ['insight_type', 'priority', 'is_active', 'is_read', 'is_implemented', 'created_at']
    search_fields = ['title', 'summary', 'detailed_analysis']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'
    actions = ['mark_as_read', 'mark_as_implemented', 'mark_as_inactive']
    
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated}개의 인사이트를 읽음으로 표시했습니다.')
    mark_as_read.short_description = '선택된 항목을 읽음으로 표시'
    
    def mark_as_implemented(self, request, queryset):
        updated = queryset.update(is_implemented=True)
        self.message_user(request, f'{updated}개의 인사이트를 구현됨으로 표시했습니다.')
    mark_as_implemented.short_description = '선택된 항목을 구현됨으로 표시'
    
    def mark_as_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated}개의 인사이트를 비활성으로 변경했습니다.')
    mark_as_inactive.short_description = '선택된 항목을 비활성으로 표시'
    
    fieldsets = (
        ('인사이트 기본 정보', {
            'fields': ('insight_type', 'title', 'priority', 'data_confidence')
        }),
        ('인사이트 내용', {
            'fields': ('summary', 'detailed_analysis', 'key_findings', 'supporting_data')
        }),
        ('실행 가능한 권고사항', {
            'fields': ('actionable_recommendations', 'expected_impact', 'implementation_steps'),
            'classes': ('collapse',)
        }),
        ('관련 정보', {
            'fields': ('related_models', 'target_audience', 'affected_areas'),
            'classes': ('collapse',)
        }),
        ('상태 정보', {
            'fields': ('is_active', 'is_read', 'is_implemented')
        }),
        ('피드백', {
            'fields': ('feedback_score', 'feedback_comments'),
            'classes': ('collapse',)
        }),
        ('메타 정보', {
            'fields': ('id', 'generated_by_model', 'reviewed_by', 'created_at'),
            'classes': ('collapse',)
        }),
    )
