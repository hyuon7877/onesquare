"""캐시 설정"""

# 캐시 백엔드 설정
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
            'CULL_FREQUENCY': 3,
        }
    },
    'session': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'session_cache_table',
    }
}

# 세션 캐시 설정
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'session'

# 캐시 미들웨어 설정
CACHE_MIDDLEWARE_ALIAS = 'default'
CACHE_MIDDLEWARE_SECONDS = 600  # 10분
CACHE_MIDDLEWARE_KEY_PREFIX = 'onesquare'

# 정적 파일 캐싱
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'