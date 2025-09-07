from django.shortcuts import render
from django.http import JsonResponse

def field_dashboard(request):
    """현장 리포트 대시보드 메인 페이지"""
    return render(request, 'field_reports/dashboard.html')

def show_qr_code(request):
    """모바일 접속용 QR 코드 페이지"""
    return render(request, 'field_reports/qr_code.html')