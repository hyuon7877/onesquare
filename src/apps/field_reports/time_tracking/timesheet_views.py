"""타임시트 관련 뷰"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from datetime import datetime, timedelta
import csv


@login_required
def timesheet_list(request):
    """타임시트 목록"""
    timesheets = get_user_timesheets(request.user)
    
    return render(request, 'field_reports/timesheet_list.html', {
        'timesheets': timesheets
    })


@login_required
def timesheet_detail(request, timesheet_id):
    """타임시트 상세"""
    timesheet = get_timesheet(timesheet_id, request.user)
    
    if not timesheet:
        messages.error(request, "타임시트를 찾을 수 없습니다.")
        return redirect('timesheet_list')
    
    return render(request, 'field_reports/timesheet_detail.html', {
        'timesheet': timesheet
    })


@login_required
def timesheet_create(request):
    """타임시트 생성"""
    if request.method == 'POST':
        timesheet = create_timesheet(request.POST, request.user)
        messages.success(request, "타임시트가 생성되었습니다.")
        return redirect('timesheet_detail', timesheet_id=timesheet.id)
    
    return render(request, 'field_reports/timesheet_form.html')


@login_required
def timesheet_submit(request, timesheet_id):
    """타임시트 제출"""
    timesheet = get_timesheet(timesheet_id, request.user)
    
    if timesheet and timesheet.status == 'draft':
        submit_timesheet(timesheet)
        messages.success(request, "타임시트가 제출되었습니다.")
    
    return redirect('timesheet_detail', timesheet_id=timesheet_id)


@login_required
def timesheet_approve(request, timesheet_id):
    """타임시트 승인 (관리자)"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    timesheet = get_timesheet(timesheet_id)
    
    if timesheet and timesheet.status == 'submitted':
        approve_timesheet(timesheet, request.user)
        return JsonResponse({'success': True})
    
    return JsonResponse({'error': 'Invalid timesheet'}, status=400)


def get_user_timesheets(user):
    """사용자 타임시트 조회"""
    # 실제 구현 필요
    return []


def get_timesheet(timesheet_id, user=None):
    """타임시트 조회"""
    # 실제 구현 필요
    return None


def create_timesheet(data, user):
    """타임시트 생성"""
    # 실제 구현 필요
    class MockTimesheet:
        id = 1
    return MockTimesheet()


def submit_timesheet(timesheet):
    """타임시트 제출"""
    # 실제 구현 필요
    pass


def approve_timesheet(timesheet, approver):
    """타임시트 승인"""
    # 실제 구현 필요
    pass
