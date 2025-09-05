"""
OneSquare 통합 관리 대시보드 시스템 - URL 설정
"""

from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # 메인 대시보드
    path('', views.dashboard_main, name='main'),
    
    # API 엔드포인트
    path('api/data/', views.dashboard_data_api, name='data_api'),
    path('api/revenue/', views.revenue_dashboard_api, name='revenue_api'),
    path('api/calendar/', views.calendar_dashboard_api, name='calendar_api'),
    path('api/system-health/', views.system_health_api, name='system_health_api'),
    path('api/notifications/', views.notifications_api, name='notifications_api'),
    path('api/notion-sync/', views.trigger_notion_sync, name='trigger_notion_sync'),
    
    # 위젯 관리
    path('widget/add/', views.add_widget, name='add_widget'),
    path('widget/layout/save/', views.save_widget_layout, name='save_widget_layout'),
    path('widget/remove/', views.remove_widget, name='remove_widget'),
    
    # 레이아웃 관리
    path('layout/reset/', views.reset_dashboard_layout, name='reset_dashboard_layout'),
    path('api/layout/', views.dashboard_layout_api, name='dashboard_layout_api'),
    path('api/user-dashboard-info/', views.user_dashboard_info_api, name='user_dashboard_info_api'),
    
    # 알림 관리
    path('notification/<uuid:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/settings/', views.notification_settings_view, name='notification_settings'),
    
    # 시스템 상태 체크
    path('status/', views.dashboard_status, name='status'),
]