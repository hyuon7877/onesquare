"""
OneSquare PWA URL 패턴
"""

from django.urls import path
from . import views

app_name = 'pwa'

urlpatterns = [
    # 오프라인 페이지
    path('offline/', views.offline_view, name='offline'),
    
    # PWA 매니페스트 및 Service Worker
    path('manifest.json', views.manifest_view, name='manifest'),
    path('sw.js', views.service_worker_view, name='service_worker'),
    path('browserconfig.xml', views.browserconfig_view, name='browserconfig'),
    
    # PWA API 엔드포인트
    path('api/status/', views.pwa_status_api, name='pwa_status'),
    path('api/install-stats/', views.pwa_install_stats, name='install_stats'),
    path('api/cache-status/', views.pwa_cache_status, name='cache_status'),
    
    # 웹 공유 대상
    path('share/', views.share_target_view, name='share_target'),
    
    # 푸시 알림 관련 API
    path('api/vapid-key/', views.vapid_public_key_view, name='vapid_key'),
    path('api/push/subscribe/', views.push_subscribe_view, name='push_subscribe'),
    path('api/push/unsubscribe/', views.push_unsubscribe_view, name='push_unsubscribe'),
    path('api/push/test/', views.push_test_view, name='push_test'),
    path('api/push/settings/', views.push_settings_view, name='push_settings'),
    path('api/push/stats/', views.push_stats_view, name='push_stats'),
]