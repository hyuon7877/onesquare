"""
OneSquare 통합 캘린더 시스템 - URL 설정
"""

from django.urls import path, include
from . import views

app_name = 'calendar_system'

urlpatterns = [
    # 메인 페이지
    path('', views.calendar_dashboard, name='dashboard'),
    
    # 이벤트 관리
    path('events/create/', views.create_event, name='create_event'),
    path('events/<int:event_id>/', views.event_detail, name='event_detail'),
    path('events/<int:event_id>/edit/', views.edit_event, name='edit_event'),
    path('events/<int:event_id>/delete/', views.delete_event, name='delete_event'),
    path('events/<int:event_id>/respond/', views.respond_to_event, name='respond_to_event'),
    path('events/my/', views.my_events, name='my_events'),
    
    # AJAX 이벤트 관리
    path('events/quick-create/', views.quick_create_event, name='quick_create_event'),
    path('events/<int:event_id>/update-time/', views.update_event_time, name='update_event_time'),
    
    # 설정
    path('settings/', views.calendar_settings_view, name='settings'),
    
    # API 엔드포인트
    path('api/events/', views.calendar_events_api, name='events_api'),
    path('api/upcoming/', views.upcoming_events_api, name='upcoming_events_api'),
    path('api/stats/', views.calendar_stats_api, name='stats_api'),
    path('api/status/', views.calendar_status, name='status'),  # 레거시 호환성
]