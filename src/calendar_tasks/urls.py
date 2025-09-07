"""캘린더 태스크 URL 설정"""
from django.urls import path
from . import views

app_name = 'calendar_tasks'

urlpatterns = [
    # 캘린더 뷰
    path('', views.CalendarListView.as_view(), name='calendar_list'),
    path('<int:pk>/', views.CalendarDetailView.as_view(), name='calendar_detail'),
    
    # 이벤트 뷰
    path('event/create/<int:calendar_id>/', views.EventCreateView.as_view(), name='event_create'),
    path('event/<int:pk>/', views.EventDetailView.as_view(), name='event_detail'),
    path('event/<int:pk>/edit/', views.EventUpdateView.as_view(), name='event_update'),
    
    # 최적화된 캘린더 뷰
    path('view/weekly/', views.WeeklyCalendarView.as_view(), name='weekly_view'),
    path('view/daily/', views.DailyCalendarView.as_view(), name='daily_view'),
    
    # API 엔드포인트
    path('api/calendar/<int:calendar_id>/events/', views.api_calendar_events, name='api_events'),
    path('api/event/create/', views.api_create_event, name='api_create_event'),
    path('api/event/<int:event_id>/update/', views.api_update_event, name='api_update_event'),
    path('api/event/<int:event_id>/delete/', views.api_delete_event, name='api_delete_event'),
    path('api/task/<int:task_id>/checklist/', views.api_task_checklist, name='api_task_checklist'),
    path('api/upcoming/', views.api_upcoming_events, name='api_upcoming'),
    path('api/overdue/', views.api_overdue_tasks, name='api_overdue'),
    path('api/summary/', views.api_calendar_summary, name='api_summary'),
]