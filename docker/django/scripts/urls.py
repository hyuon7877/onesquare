# -*- coding: utf-8 -*-
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.http import JsonResponse

def index(request):
    """메인 페이지 API"""
    return JsonResponse({
        'project': settings.PROJECT_NAME,
        'version': settings.PROJECT_VERSION,
        'status': 'healthy',
        'language': settings.LANGUAGE_CODE,
        'timezone': settings.TIME_ZONE,
        'debug': settings.DEBUG,
        'message': '🚀 Django 프로젝트가 성공적으로 실행중입니다!'
    }, json_dumps_params={'ensure_ascii': False})

def health_check(request):
    """헬스체크 엔드포인트"""
    return JsonResponse({'status': 'healthy'})

urlpatterns = [
    path('', index, name='index'),
    path('health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('api/', include('rest_framework.urls')),
    path('api/v1/', include('main.urls')),
]

# Static/Media 파일 서빙 (개발 환경)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Debug Toolbar
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
        path('silk/', include('silk.urls', namespace='silk')),
    ] + urlpatterns

# Admin 사이트 설정
admin.site.site_header = f'{settings.PROJECT_NAME} 관리'
admin.site.site_title = f'{settings.PROJECT_NAME}'
admin.site.index_title = '관리 홈'
