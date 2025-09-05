"""
피드백 시스템 URL 설정
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# DRF Router 설정
router = DefaultRouter()
router.register(r'threads', views.FeedbackThreadViewSet, basename='thread')
router.register(r'messages', views.FeedbackMessageViewSet, basename='message')
router.register(r'attachments', views.MediaAttachmentViewSet, basename='attachment')
router.register(r'notifications', views.FeedbackNotificationViewSet, basename='notification')

app_name = 'feedback'

urlpatterns = [
    # API URLs
    path('api/', include(router.urls)),
    
    # PWA 템플릿 URLs
    path('', views.feedback_dashboard, name='dashboard'),
    path('thread/<uuid:thread_id>/', views.thread_detail, name='thread_detail'),
    path('create/', views.create_thread, name='create_thread'),
]