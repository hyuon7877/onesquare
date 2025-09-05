from django.urls import path
from . import views

app_name = 'leave_management'

urlpatterns = [
    # 메인 페이지
    path('', views.leave_dashboard, name='dashboard'),
    
    # 연차 신청
    path('request/', views.leave_request, name='request'),
    
    # 승인/반려/취소
    path('approve/<int:request_id>/', views.approve_leave, name='approve'),
    path('reject/<int:request_id>/', views.reject_leave, name='reject'),
    path('cancel/<int:request_id>/', views.cancel_leave, name='cancel'),
    
    # API 엔드포인트
    path('api/calendar/', views.api_leave_calendar, name='api_calendar'),
    path('api/balance/', views.api_leave_balance, name='api_balance'),
]