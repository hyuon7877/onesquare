from django.urls import path
from . import views

app_name = 'calendar'

urlpatterns = [
    # 캘린더 메인 페이지
    path('', views.calendar_view, name='calendar'),
    
    # 캘린더 API 엔드포인트
    path('api/events/', views.get_calendar_events, name='api_events'),
    path('api/events/create/', views.create_calendar_event, name='api_create'),
    path('api/events/<int:event_id>/update/', views.update_calendar_event, name='api_update'),
    path('api/events/<int:event_id>/delete/', views.delete_calendar_event, name='api_delete'),
]