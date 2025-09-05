"""
OneSquare Time Management - URL 패턴

업무시간 관리 시스템의 URL 라우팅 설정
"""

from django.urls import path, include
from . import views

app_name = 'time_management'

# API URL 패턴
api_urlpatterns = [
    # 근무시간 추적 API
    path('check-in/', views.check_in, name='api_check_in'),
    path('check-out/', views.check_out, name='api_check_out'),
    path('work-status/', views.work_status, name='api_work_status'),
    
    # 근무기록 조회 API
    path('daily-records/', views.daily_records, name='api_daily_records'),
    path('records/<int:record_id>/memo/', views.update_memo, name='api_update_memo'),
    
    # 통계 API
    path('statistics/monthly/', views.monthly_statistics, name='api_monthly_statistics'),
    path('statistics/weekly/', views.weekly_statistics, name='api_weekly_statistics'),
    path('chart-data/', views.chart_data, name='api_chart_data'),
    
    # 관리자 API
    path('records/<int:record_id>/adjust/', views.adjust_work_time, name='api_adjust_work_time'),
    path('statistics/cache/', views.update_statistics_cache, name='api_update_statistics_cache'),
    
    # Notion 연동 API
    path('records/<int:record_id>/sync/', views.sync_to_notion, name='api_sync_to_notion'),
    
    # 내보내기
    path('export/monthly-excel/', views.export_monthly_excel, name='api_export_monthly_excel'),
]

# 메인 URL 패턴
urlpatterns = [
    # PWA 메인 대시보드
    path('', views.time_management_dashboard, name='dashboard'),
    
    # API 엔드포인트
    path('api/', include(api_urlpatterns)),
]