"""
OneSquare 매출 관리 시스템 - URL 설정
"""

from django.urls import path
from . import views, sync_views, alert_views

app_name = 'revenue'

urlpatterns = [
    # 대시보드 및 메인 페이지
    path('', views.revenue_dashboard_view, name='dashboard'),
    path('list/', views.revenue_list_view, name='list'),
    
    # API 엔드포인트
    path('api/dashboard/', views.revenue_dashboard_data, name='dashboard_api'),
    path('api/list/', views.revenue_list_api, name='list_api'),
    path('api/analytics/', views.revenue_analytics, name='analytics_api'),
    path('api/targets/progress/', views.revenue_targets_progress, name='targets_progress_api'),
    path('api/export/', views.revenue_export, name='export_api'),
    
    # Notion 동기화 API
    path('api/sync/status/', sync_views.NotionSyncStatusView.as_view(), name='sync_status'),
    path('api/sync/trigger/', sync_views.trigger_full_sync, name='sync_trigger'),
    path('api/sync/revenue/<uuid:revenue_id>/', sync_views.sync_single_revenue, name='sync_single'),
    path('api/sync/history/', sync_views.sync_history, name='sync_history'),
    path('api/sync/clear-cache/', sync_views.clear_sync_cache, name='sync_clear_cache'),
    path('api/sync/config-check/', sync_views.notion_config_check, name='sync_config_check'),
    
    # Notion 웹훅 (실시간 동기화)
    path('webhook/notion/', sync_views.notion_webhook, name='notion_webhook'),
    
    # 알림 시스템 API
    path('api/alerts/', alert_views.get_user_alerts, name='user_alerts'),
    path('api/alerts/summary/', alert_views.get_alert_summary, name='alert_summary'),
    path('api/alerts/widgets/', alert_views.get_dashboard_widgets, name='dashboard_widgets'),
    path('api/alerts/history/', alert_views.get_alert_history, name='alert_history'),
    path('api/alerts/statistics/', alert_views.get_alert_statistics, name='alert_statistics'),
    path('api/alerts/<uuid:alert_id>/read/', alert_views.mark_alert_read, name='mark_alert_read'),
    path('api/alerts/create/', alert_views.create_custom_alert, name='create_alert'),
    path('api/alerts/refresh/', alert_views.trigger_alert_refresh, name='refresh_alerts'),
    
    # PWA 푸시 알림
    path('api/push/subscribe/', alert_views.subscribe_push_notifications, name='push_subscribe'),
    
    # 외부 알림 웹훅
    path('webhook/alerts/', alert_views.webhook_alert_trigger, name='alert_webhook'),
]