"""
OneSquare Notion API 연동 - URL 패턴

이 모듈은 Notion API 관련 모든 엔드포인트를 정의합니다.
"""

from django.urls import path, include
from . import views

app_name = 'notion_api'

urlpatterns = [
    # 기본 API
    path('test/', views.notion_test_api, name='notion_test'),
    path('sync/', views.notion_sync_api, name='notion_sync'),  # 레거시
    
    # 데이터베이스 관리
    path('databases/', views.NotionDatabaseListView.as_view(), name='database_list'),
    path('databases/<int:pk>/', views.NotionDatabaseDetailView.as_view(), name='database_detail'),
    
    # 페이지 관리
    path('databases/<int:database_id>/pages/', views.NotionPageListView.as_view(), name='page_list'),
    path('pages/<int:page_id>/', views.NotionPageDetailView.as_view(), name='page_detail'),
    
    # 동기화
    path('databases/<int:database_id>/sync/', views.DatabaseSyncView.as_view(), name='database_sync'),
    path('databases/<int:database_id>/push/', views.push_local_changes, name='push_changes'),
    
    # 동기화 기록
    path('sync-history/', views.SyncHistoryView.as_view(), name='sync_history'),
    path('databases/<int:database_id>/sync-history/', views.SyncHistoryView.as_view(), name='database_sync_history'),
    
    # 관리자 기능
    path('databases/<int:database_id>/refresh-schema/', views.refresh_database_schema, name='refresh_schema'),
    path('cache/clear/', views.clear_cache, name='clear_cache'),
    
    # 검색 및 유틸리티
    path('search/', views.search_notion_workspace, name='workspace_search'),
]