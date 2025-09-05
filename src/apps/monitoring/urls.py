"""
모니터링 앱 URL 패턴
"""
from django.urls import path
from . import views

app_name = 'monitoring'

urlpatterns = [
    # 대시보드
    path('', views.MonitoringDashboardView.as_view(), name='dashboard'),
    
    # API 엔드포인트들
    path('api/system-metrics/', views.system_metrics_api, name='system_metrics_api'),
    path('api/performance-metrics/', views.performance_metrics_api, name='performance_metrics_api'),
    path('api/notion-api-metrics/', views.notion_api_metrics_api, name='notion_api_metrics_api'),
    path('api/user-activity/', views.user_activity_api, name='user_activity_api'),
    path('api/error-logs/', views.error_logs_api, name='error_logs_api'),
    path('api/alerts/', views.alerts_api, name='alerts_api'),
    path('api/health-check/', views.health_check_api, name='health_check_api'),
]