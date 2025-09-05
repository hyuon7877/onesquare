"""
OneSquare AI 데이터 분석 뷰
매출 예측, 업무 효율성 분석, 성과 분석을 위한 뷰들
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db.models import Q, Sum, Avg, Count
from django.utils import timezone
from datetime import datetime, date, timedelta
from decimal import Decimal
import json

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import (
    AIModelConfig, RevenuePrediction, WorkEfficiencyAnalysis, 
    PerformanceAnalysis, AnomalyDetection, AIInsight
)
from .services import (
    RevenuePredictionService, WorkEfficiencyService, 
    PerformanceAnalysisService, AnomalyDetectionService, AIInsightService
)
from apps.revenue.models import Project, RevenueRecord

@login_required
def analytics_dashboard(request):
    """AI 분석 대시보드"""
    # 최근 인사이트 조회
    recent_insights = AIInsight.objects.filter(
        is_active=True
    ).order_by('-priority', '-created_at')[:5]
    
    # 최근 예측 조회
    recent_predictions = RevenuePrediction.objects.filter(
        target_period_start__gte=timezone.now().date()
    ).order_by('-created_at')[:3]
    
    # 최근 이상 감지
    recent_anomalies = AnomalyDetection.objects.filter(
        status='detected'
    ).order_by('-detected_at')[:5]
    
    # 성과 분석 요약
    recent_performance = PerformanceAnalysis.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=30)
    ).order_by('-created_at')[:3]
    
    context = {
        'recent_insights': recent_insights,
        'recent_predictions': recent_predictions,
        'recent_anomalies': recent_anomalies,
        'recent_performance': recent_performance,
        'total_insights': AIInsight.objects.filter(is_active=True).count(),
        'total_predictions': RevenuePrediction.objects.count(),
        'total_anomalies': AnomalyDetection.objects.filter(status='detected').count(),
        'page_title': 'AI 데이터 분석 대시보드'
    }
    
    return render(request, 'ai_analytics/dashboard.html', context)

@login_required 
def revenue_prediction_list(request):
    """매출 예측 목록"""
    predictions = RevenuePrediction.objects.select_related('model').order_by('-created_at')
    
    # 필터링
    prediction_type = request.GET.get('type')
    if prediction_type:
        predictions = predictions.filter(prediction_type=prediction_type)
    
    confidence_level = request.GET.get('confidence')
    if confidence_level:
        predictions = predictions.filter(confidence_level=confidence_level)
    
    context = {
        'predictions': predictions,
        'prediction_types': RevenuePrediction.PREDICTION_TYPE_CHOICES,
        'confidence_levels': RevenuePrediction.CONFIDENCE_LEVEL_CHOICES,
        'page_title': '매출 예측 목록'
    }
    
    return render(request, 'ai_analytics/prediction_list.html', context)

@login_required
def revenue_prediction_detail(request, prediction_id):
    """매출 예측 상세"""
    prediction = get_object_or_404(RevenuePrediction, id=prediction_id)
    
    # 관련 실제 매출 데이터 (검증용)
    actual_revenues = None
    if prediction.actual_amount:
        actual_revenues = RevenueRecord.objects.filter(
            revenue_date__range=[prediction.target_period_start, prediction.target_period_end],
            is_confirmed=True
        ).order_by('revenue_date')
    
    context = {
        'prediction': prediction,
        'actual_revenues': actual_revenues,
        'accuracy': prediction.calculate_accuracy(),
        'page_title': f'매출 예측 상세 - {prediction.get_prediction_type_display()}'
    }
    
    return render(request, 'ai_analytics/prediction_detail.html', context)

@login_required
def efficiency_analysis_list(request):
    """업무 효율성 분석 목록"""
    analyses = WorkEfficiencyAnalysis.objects.select_related('target_user', 'target_project').order_by('-created_at')
    
    # 필터링
    analysis_type = request.GET.get('type')
    if analysis_type:
        analyses = analyses.filter(analysis_type=analysis_type)
    
    efficiency_level = request.GET.get('level')
    if efficiency_level:
        analyses = analyses.filter(efficiency_level=efficiency_level)
    
    context = {
        'analyses': analyses,
        'analysis_types': WorkEfficiencyAnalysis.ANALYSIS_TYPE_CHOICES,
        'efficiency_levels': WorkEfficiencyAnalysis.EFFICIENCY_LEVEL_CHOICES,
        'page_title': '업무 효율성 분석 목록'
    }
    
    return render(request, 'ai_analytics/efficiency_list.html', context)

@login_required
def performance_analysis_list(request):
    """성과 분석 목록"""
    analyses = PerformanceAnalysis.objects.select_related(
        'target_user', 'target_project'
    ).order_by('-created_at')
    
    # 필터링
    performance_type = request.GET.get('type')
    if performance_type:
        analyses = analyses.filter(performance_type=performance_type)
    
    performance_grade = request.GET.get('grade')
    if performance_grade:
        analyses = analyses.filter(performance_grade=performance_grade)
    
    context = {
        'analyses': analyses,
        'performance_types': PerformanceAnalysis.PERFORMANCE_TYPE_CHOICES,
        'performance_grades': PerformanceAnalysis.PERFORMANCE_GRADE_CHOICES,
        'page_title': '성과 분석 목록'
    }
    
    return render(request, 'ai_analytics/performance_list.html', context)

@login_required
def anomaly_detection_list(request):
    """이상 패턴 감지 목록"""
    anomalies = AnomalyDetection.objects.select_related(
        'related_user', 'related_project'
    ).order_by('-detected_at')
    
    # 필터링
    anomaly_type = request.GET.get('type')
    if anomaly_type:
        anomalies = anomalies.filter(anomaly_type=anomaly_type)
    
    severity = request.GET.get('severity')
    if severity:
        anomalies = anomalies.filter(severity=severity)
    
    status_filter = request.GET.get('status')
    if status_filter:
        anomalies = anomalies.filter(status=status_filter)
    
    context = {
        'anomalies': anomalies,
        'anomaly_types': AnomalyDetection.ANOMALY_TYPE_CHOICES,
        'severity_choices': AnomalyDetection.SEVERITY_CHOICES,
        'status_choices': AnomalyDetection.STATUS_CHOICES,
        'page_title': '이상 패턴 감지 목록'
    }
    
    return render(request, 'ai_analytics/anomaly_list.html', context)

@login_required
def ai_insights_list(request):
    """AI 인사이트 목록"""
    insights = AIInsight.objects.filter(is_active=True).order_by('-priority', '-created_at')
    
    # 필터링
    insight_type = request.GET.get('type')
    if insight_type:
        insights = insights.filter(insight_type=insight_type)
    
    priority = request.GET.get('priority')
    if priority:
        insights = insights.filter(priority=priority)
    
    context = {
        'insights': insights,
        'insight_types': AIInsight.INSIGHT_TYPE_CHOICES,
        'priority_choices': AIInsight.PRIORITY_CHOICES,
        'page_title': 'AI 인사이트 목록'
    }
    
    return render(request, 'ai_analytics/insights_list.html', context)

@login_required
def ai_insight_detail(request, insight_id):
    """AI 인사이트 상세"""
    insight = get_object_or_404(AIInsight, id=insight_id)
    
    # 읽음 상태 업데이트
    if not insight.is_read:
        insight.is_read = True
        insight.save(update_fields=['is_read'])
    
    context = {
        'insight': insight,
        'page_title': f'AI 인사이트 - {insight.title}'
    }
    
    return render(request, 'ai_analytics/insight_detail.html', context)

# API 엔드포인트들
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_revenue_prediction(request):
    """매출 예측 생성 API"""
    try:
        prediction_type = request.data.get('type', 'monthly')
        months_ahead = int(request.data.get('months_ahead', 3))
        model_type = request.data.get('model_type', 'linear_regression')
        
        service = RevenuePredictionService()
        
        if prediction_type == 'project':
            project_id = request.data.get('project_id')
            if not project_id:
                return Response({'error': '프로젝트 ID가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)
            
            project = get_object_or_404(Project, id=project_id)
            prediction = service.create_project_prediction(project)
        else:
            prediction = service.create_monthly_prediction(months_ahead, model_type)
        
        return Response({
            'id': str(prediction.id),
            'prediction_type': prediction.get_prediction_type_display(),
            'predicted_amount': float(prediction.predicted_amount),
            'confidence_score': prediction.confidence_score,
            'target_period': f"{prediction.target_period_start} ~ {prediction.target_period_end}",
            'message': '예측이 성공적으로 생성되었습니다.'
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_user_efficiency(request):
    """사용자 효율성 분석 API"""
    try:
        user_id = request.data.get('user_id', request.user.id)
        start_date = datetime.strptime(request.data.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(request.data.get('end_date'), '%Y-%m-%d').date()
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = get_object_or_404(User, id=user_id)
        
        service = WorkEfficiencyService()
        analysis = service.analyze_user_efficiency(user, start_date, end_date)
        
        return Response({
            'id': str(analysis.id),
            'efficiency_score': analysis.efficiency_score,
            'efficiency_level': analysis.get_efficiency_level_display(),
            'strengths': analysis.strengths,
            'weaknesses': analysis.weaknesses,
            'recommendations': analysis.recommendations,
            'message': '효율성 분석이 완료되었습니다.'
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_sales_performance(request):
    """영업 성과 분석 API"""
    try:
        user_id = request.data.get('user_id', request.user.id)
        start_date = datetime.strptime(request.data.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(request.data.get('end_date'), '%Y-%m-%d').date()
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = get_object_or_404(User, id=user_id)
        
        service = PerformanceAnalysisService()
        analysis = service.analyze_sales_performance(user, start_date, end_date)
        
        return Response({
            'id': str(analysis.id),
            'overall_score': analysis.overall_score,
            'performance_grade': analysis.performance_grade,
            'kpi_scores': analysis.kpi_scores,
            'achievements': analysis.achievements,
            'challenges': analysis.challenges,
            'message': '성과 분석이 완료되었습니다.'
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def detect_anomalies(request):
    """이상 패턴 감지 API"""
    try:
        detection_type = request.data.get('type', 'revenue')
        
        service = AnomalyDetectionService()
        
        if detection_type == 'revenue':
            anomalies = service.detect_revenue_anomalies()
        elif detection_type == 'efficiency':
            user_id = request.data.get('user_id', request.user.id)
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = get_object_or_404(User, id=user_id)
            anomalies = service.detect_efficiency_anomalies(user)
        else:
            return Response({'error': '지원하지 않는 감지 유형입니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
        anomaly_data = []
        for anomaly in anomalies:
            anomaly_data.append({
                'id': str(anomaly.id),
                'type': anomaly.get_anomaly_type_display(),
                'severity': anomaly.get_severity_display(),
                'description': anomaly.description,
                'detected_at': anomaly.detected_at.isoformat()
            })
        
        return Response({
            'anomalies': anomaly_data,
            'count': len(anomalies),
            'message': f'{len(anomalies)}개의 이상 패턴이 감지되었습니다.'
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_insights(request):
    """AI 인사이트 생성 API"""
    try:
        insight_category = request.data.get('category', 'revenue')
        
        service = AIInsightService()
        
        if insight_category == 'revenue':
            insights = service.generate_revenue_insights()
        elif insight_category == 'efficiency':
            insights = service.generate_efficiency_insights()
        else:
            return Response({'error': '지원하지 않는 인사이트 카테고리입니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
        insight_data = []
        for insight in insights:
            insight_data.append({
                'id': str(insight.id),
                'type': insight.get_insight_type_display(),
                'title': insight.title,
                'priority': insight.get_priority_display(),
                'summary': insight.summary,
                'recommendations': insight.actionable_recommendations
            })
        
        return Response({
            'insights': insight_data,
            'count': len(insights),
            'message': f'{len(insights)}개의 새로운 인사이트가 생성되었습니다.'
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_summary(request):
    """분석 요약 정보 API"""
    try:
        # 기본 통계
        total_predictions = RevenuePrediction.objects.count()
        total_analyses = WorkEfficiencyAnalysis.objects.count()
        total_performance = PerformanceAnalysis.objects.count()
        total_anomalies = AnomalyDetection.objects.count()
        active_insights = AIInsight.objects.filter(is_active=True).count()
        
        # 최근 활동
        recent_activity = []
        
        # 최근 예측
        recent_predictions = RevenuePrediction.objects.order_by('-created_at')[:3]
        for pred in recent_predictions:
            recent_activity.append({
                'type': 'prediction',
                'title': f'매출 예측: {pred.predicted_amount:,}원',
                'date': pred.created_at.isoformat(),
                'confidence': pred.confidence_score
            })
        
        # 최근 이상 감지
        recent_anomalies = AnomalyDetection.objects.filter(
            status='detected'
        ).order_by('-detected_at')[:3]
        
        for anomaly in recent_anomalies:
            recent_activity.append({
                'type': 'anomaly',
                'title': f'이상 감지: {anomaly.get_anomaly_type_display()}',
                'date': anomaly.detected_at.isoformat(),
                'severity': anomaly.severity
            })
        
        # 시간순 정렬
        recent_activity.sort(key=lambda x: x['date'], reverse=True)
        
        return Response({
            'summary': {
                'total_predictions': total_predictions,
                'total_analyses': total_analyses,
                'total_performance': total_performance,
                'total_anomalies': total_anomalies,
                'active_insights': active_insights
            },
            'recent_activity': recent_activity[:10],
            'model_status': {
                'active_models': AIModelConfig.objects.filter(status='active').count(),
                'total_models': AIModelConfig.objects.count()
            }
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_insight_feedback(request, insight_id):
    """AI 인사이트 피드백 업데이트 API"""
    try:
        insight = get_object_or_404(AIInsight, id=insight_id)
        
        feedback_score = request.data.get('score')
        feedback_comments = request.data.get('comments', '')
        is_implemented = request.data.get('is_implemented', False)
        
        if feedback_score:
            insight.feedback_score = float(feedback_score)
        
        if feedback_comments:
            insight.feedback_comments = feedback_comments
        
        insight.is_implemented = is_implemented
        insight.save()
        
        return Response({
            'message': '피드백이 성공적으로 업데이트되었습니다.',
            'insight_id': str(insight.id)
        })
        
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@require_http_methods(["POST"])
@login_required
def update_anomaly_status(request, anomaly_id):
    """이상 패턴 상태 업데이트"""
    try:
        anomaly = get_object_or_404(AnomalyDetection, id=anomaly_id)
        
        new_status = request.POST.get('status')
        resolution_notes = request.POST.get('resolution_notes', '')
        
        if new_status in dict(AnomalyDetection.STATUS_CHOICES):
            anomaly.status = new_status
            if resolution_notes:
                anomaly.resolution_notes = resolution_notes
            
            if new_status == 'resolved':
                anomaly.resolved_at = timezone.now()
                anomaly.investigated_by = request.user
            
            anomaly.save()
            messages.success(request, '이상 패턴 상태가 업데이트되었습니다.')
        else:
            messages.error(request, '잘못된 상태값입니다.')
    
    except Exception as e:
        messages.error(request, f'오류가 발생했습니다: {str(e)}')
    
    return JsonResponse({
        'success': anomaly.status == new_status if 'anomaly' in locals() else False,
        'new_status': anomaly.get_status_display() if 'anomaly' in locals() else None
    })
