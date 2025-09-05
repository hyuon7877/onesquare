"""
OneSquare 현장 리포트 시스템 URL 패턴
"""

from django.urls import path
from . import views, time_tracking_views, photo_views, inventory_views

app_name = 'field_report'

urlpatterns = [
    # 메인 대시보드
    path('', views.field_dashboard, name='dashboard'),
    
    # 업무 세션 관리
    path('session/start/', views.start_work_session, name='start_session'),
    path('session/<uuid:session_id>/end/', views.end_work_session, name='end_session'),
    path('session/<uuid:session_id>/pause/', views.pause_work_session, name='pause_session'),
    path('session/<uuid:session_id>/resume/', views.resume_work_session, name='resume_session'),
    
    # 체크리스트 및 리포트
    path('session/<uuid:session_id>/checklist/', views.checklist_view, name='checklist'),
    path('session/<uuid:session_id>/save-progress/', views.save_checklist_progress, name='save_progress'),
    
    # 사진 업로드
    path('report/<uuid:report_id>/upload-photos/', views.upload_report_photos, name='upload_photos'),
    
    # 재고 관리
    path('report/<uuid:report_id>/inventory/', views.inventory_check_view, name='inventory_check'),
    path('report/<uuid:report_id>/save-inventory/', views.save_inventory_check, name='save_inventory'),
    
    # 시간 추적 템플릿
    path('time-tracker/', time_tracking_views.time_tracker_view, name='time_tracker'),
    path('photo-upload/', views.photo_upload_view, name='photo_upload_view'),
    path('inventory-check/', views.inventory_check_view, name='inventory_check_view'),
    
    # API 엔드포인트 - 시간 추적
    path('api/sites/', time_tracking_views.api_field_sites, name='api_sites'),
    path('api/current-session/', time_tracking_views.api_current_session, name='api_current_session'),
    path('api/start-work/', time_tracking_views.api_start_work, name='api_start_work'),
    path('api/end-work/', time_tracking_views.api_end_work, name='api_end_work'),
    path('api/recent-sessions/', time_tracking_views.api_recent_sessions, name='api_recent_sessions'),
    
    # API 엔드포인트 - 사진 업로드
    path('api/upload-photo/', photo_views.upload_photo, name='api_upload_photo'),
    path('api/batch-upload/', photo_views.batch_upload_photos, name='api_batch_upload'),
    path('api/upload-progress/', photo_views.upload_progress, name='api_upload_progress'),
    path('api/photo-list/', photo_views.photo_list, name='api_photo_list'),
    path('api/photo/<uuid:photo_id>/delete/', photo_views.delete_photo, name='api_delete_photo'),
    path('api/photo-stats/', photo_views.photo_stats, name='api_photo_stats'),
    
    # API 엔드포인트 - 재고 관리
    path('api/inventory-items/', inventory_views.inventory_items, name='api_inventory_items'),
    path('api/save-inventory-check/', inventory_views.save_inventory_check, name='api_save_inventory_check'),
    path('api/save-all-inventory-checks/', inventory_views.save_all_inventory_checks, name='api_save_all_inventory_checks'),
    path('api/inventory-stats/', inventory_views.inventory_stats, name='api_inventory_stats'),
    path('api/low-stock-alerts/', inventory_views.low_stock_alerts, name='api_low_stock_alerts'),
    path('api/inventory-history/', inventory_views.inventory_history, name='api_inventory_history'),
    
    # 기존 API 엔드포인트
    path('api/session-status/', views.api_work_session_status, name='api_session_status'),
    path('api/reports-summary/', views.api_reports_summary, name='api_reports_summary'),
]