from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/comments/(?P<content_type>\w+)/(?P<object_id>\d+)/$', 
            consumers.CommentConsumer.as_asgi()),
    re_path(r'ws/notifications/$', 
            consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/presence/$', 
            consumers.PresenceConsumer.as_asgi()),
    re_path(r'ws/activity/$', 
            consumers.ActivityConsumer.as_asgi()),
]