from django.urls import path
from . import views

app_name = 'field_reports'

urlpatterns = [
    # 리포트 목록
    path('', views.report_list, name='report_list'),
    
    # 리포트 작성
    path('create/', views.report_create, name='report_create'),
    
    # 리포트 상세
    path('<int:pk>/', views.report_detail, name='report_detail'),
    
    # 리포트 수정
    path('<int:pk>/edit/', views.report_edit, name='report_edit'),
    
    # 리포트 삭제
    path('<int:pk>/delete/', views.report_delete, name='report_delete'),
    
    # 파일 업로드 (AJAX)
    path('<int:pk>/upload/', views.upload_attachment, name='upload_attachment'),
    
    # 오프라인 저장 (PWA)
    path('offline/save/', views.save_offline_report, name='save_offline'),
    
    # 동기화
    path('sync/', views.sync_reports, name='sync_reports'),
]