from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('team/', views.team_management_view, name='team'),
    path('api/statistics/', views.get_statistics, name='api_statistics'),
    path('api/recent-activities/', views.get_recent_activities, name='api_recent_activities'),
    path('api/activities/', views.get_recent_activities, name='api_activities'),  # alias for compatibility
    path('api/notifications/', views.get_notifications, name='api_notifications'),
    path('api/chart-data/', views.get_chart_data, name='api_chart_data'),
    path('api/chart/', views.get_chart_data, name='api_chart'),  # alias for compatibility
    path('api/notification/read/', views.mark_notification_read, name='api_notification_read'),
    
    # 캘린더 API 엔드포인트
    path('api/calendar/events/', views.get_calendar_events, name='api_calendar_events'),
    path('api/calendar/events/create/', views.create_calendar_event, name='api_calendar_create'),
    path('api/calendar/events/<int:event_id>/update/', views.update_calendar_event, name='api_calendar_update'),
    path('api/calendar/events/<int:event_id>/delete/', views.delete_calendar_event, name='api_calendar_delete'),
]