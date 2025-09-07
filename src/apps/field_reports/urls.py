"""
OneSquare 현장 리포트 시스템 URL 패턴
"""

from django.urls import path
from . import simple_views

app_name = 'field_report'

urlpatterns = [
    # 메인 대시보드
    path('', simple_views.field_dashboard, name='dashboard'),
    # QR 코드 페이지
    path('qr/', simple_views.show_qr_code, name='qr_code'),
]