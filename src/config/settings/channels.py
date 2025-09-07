"""Django Channels 설정"""
import os

# ASGI Application
ASGI_APPLICATION = 'config.asgi.application'

# Channel Layer Configuration
CHANNEL_LAYERS = {
    'default': {
        # 개발 환경에서는 In-memory channel layer 사용
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
        # 운영 환경에서는 Redis 사용 (requirements.txt에 channels-redis 필요)
        # 'BACKEND': 'channels_redis.core.RedisChannelLayer',
        # 'CONFIG': {
        #     "hosts": [('127.0.0.1', 6379)],
        # },
    }
}

# WebSocket 관련 설정
WEBSOCKET_ACCEPT_ALL = True  # 개발 환경용