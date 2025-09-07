from django.urls import path
from . import views

app_name = 'collaboration'

urlpatterns = [
    # 협업 홈 페이지
    path('', views.collaboration_home, name='home'),
    
    # 댓글
    path('comments/<int:content_type_id>/<int:object_id>/', views.comment_list, name='comment_list'),
    path('comments/<int:comment_id>/', views.comment_detail, name='comment_detail'),
    
    # 활동 피드
    path('activities/', views.activity_feed, name='activity_feed'),
    
    # 알림
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/read-all/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    
    # 사용자 상태
    path('presence/update/', views.update_presence, name='update_presence'),
    path('presence/online/', views.get_online_users, name='get_online_users'),
    
    # 사용자 검색 (멘션용)
    path('users/search/', views.search_users, name='search_users'),
]