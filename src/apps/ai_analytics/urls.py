"""
AI Analytics URL 패턴 설정
"""

from django.urls import path
from . import views

app_name = 'ai_analytics'

urlpatterns = [
    # 대시보드 및 메인 페이지
    path('', views.analytics_dashboard, name='dashboard'),
    
    # 매출 예측
    path('predictions/', views.revenue_prediction_list, name='prediction_list'),
    path('predictions/<uuid:prediction_id>/', views.revenue_prediction_detail, name='prediction_detail'),
    
    # 업무 효율성 분석
    path('efficiency/', views.efficiency_analysis_list, name='efficiency_list'),
    
    # 성과 분석
    path('performance/', views.performance_analysis_list, name='performance_list'),
    
    # 이상 패턴 감지
    path('anomalies/', views.anomaly_detection_list, name='anomaly_list'),
    path('anomalies/<uuid:anomaly_id>/update-status/', views.update_anomaly_status, name='update_anomaly_status'),
    
    # AI 인사이트
    path('insights/', views.ai_insights_list, name='insights_list'),
    path('insights/<uuid:insight_id>/', views.ai_insight_detail, name='insight_detail'),
    
    # API 엔드포인트
    path('api/predictions/create/', views.create_revenue_prediction, name='api_create_prediction'),
    path('api/efficiency/analyze/', views.analyze_user_efficiency, name='api_analyze_efficiency'),
    path('api/performance/analyze/', views.analyze_sales_performance, name='api_analyze_performance'),
    path('api/anomalies/detect/', views.detect_anomalies, name='api_detect_anomalies'),
    path('api/insights/generate/', views.generate_insights, name='api_generate_insights'),
    path('api/insights/<uuid:insight_id>/feedback/', views.update_insight_feedback, name='api_insight_feedback'),
    path('api/summary/', views.analytics_summary, name='api_summary'),
]