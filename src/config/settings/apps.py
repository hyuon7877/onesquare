"""Installed apps"""
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Django Channels (설치 후 활성화)
    # 'channels',
    # 'daphne',
    
    # 내부 앱들
    'accounts',
    'dashboard',
    'field_reports',
    'collaboration',
    'search',
]
