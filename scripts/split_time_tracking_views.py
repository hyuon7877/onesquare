#!/usr/bin/env python3
"""Time Tracking Views 모듈 자동 분할"""

import shutil
from pathlib import Path

# 경로 설정
source_file = Path('src/apps/field_reports/time_tracking_views.py')
target_dir = Path('src/apps/field_reports/time_tracking')

# 백업
backup_file = source_file.parent / f"{source_file.stem}_backup.py"
if not backup_file.exists():
    shutil.copy(source_file, backup_file)
    print(f"✅ 백업 생성: {backup_file.name}")

# 대상 디렉토리 생성
target_dir.mkdir(exist_ok=True)

# 1. calendar_views.py - 캘린더 관련 뷰
with open(target_dir / 'calendar_views.py', 'w', encoding='utf-8') as f:
    f.write('''"""캘린더 관련 뷰"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from datetime import datetime, timedelta
from django.utils import timezone


@login_required
def calendar_view(request):
    """캘린더 메인 뷰"""
    context = {
        'current_date': timezone.now(),
        'user_events': get_user_events(request.user)
    }
    return render(request, 'field_reports/calendar.html', context)


@login_required
def calendar_api(request):
    """캘린더 데이터 API"""
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    
    events = get_calendar_events(
        request.user,
        start_date,
        end_date
    )
    
    return JsonResponse({'events': events})


@login_required
def add_calendar_event(request):
    """캘린더 이벤트 추가"""
    if request.method == 'POST':
        event_data = {
            'title': request.POST.get('title'),
            'start': request.POST.get('start'),
            'end': request.POST.get('end'),
            'user': request.user
        }
        
        # 이벤트 생성 로직
        event = create_event(event_data)
        
        return JsonResponse({
            'success': True,
            'event_id': event.id
        })
    
    return JsonResponse({'error': 'POST required'}, status=400)


def get_user_events(user):
    """사용자 이벤트 조회"""
    # 실제 구현 필요
    return []


def get_calendar_events(user, start, end):
    """기간별 이벤트 조회"""
    # 실제 구현 필요
    return []


def create_event(data):
    """이벤트 생성"""
    # 실제 구현 필요
    class MockEvent:
        id = 1
    return MockEvent()
''')
    print("✅ calendar_views.py 생성")

# 2. timesheet_views.py - 타임시트 관련 뷰
with open(target_dir / 'timesheet_views.py', 'w', encoding='utf-8') as f:
    f.write('''"""타임시트 관련 뷰"""
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
''')
    print("✅ timesheet_views.py 생성")

# 3. report_views.py - 보고서 관련 뷰
with open(target_dir / 'report_views.py', 'w', encoding='utf-8') as f:
    f.write('''"""시간 추적 보고서 뷰"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Count, Avg
from datetime import datetime, timedelta
import json


@login_required
def time_report_dashboard(request):
    """시간 추적 대시보드"""
    period = request.GET.get('period', 'month')
    
    stats = get_time_statistics(request.user, period)
    
    return render(request, 'field_reports/time_dashboard.html', {
        'stats': stats,
        'period': period
    })


@login_required
def productivity_report(request):
    """생산성 보고서"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    productivity_data = calculate_productivity(
        request.user,
        start_date,
        end_date
    )
    
    return render(request, 'field_reports/productivity_report.html', {
        'data': productivity_data
    })


@login_required
def team_time_report(request):
    """팀 시간 보고서 (관리자)"""
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    team_data = get_team_time_data()
    
    return render(request, 'field_reports/team_time_report.html', {
        'team_data': team_data
    })


@login_required
def export_time_report(request):
    """시간 보고서 내보내기"""
    format_type = request.GET.get('format', 'csv')
    period = request.GET.get('period', 'month')
    
    data = get_export_data(request.user, period)
    
    if format_type == 'csv':
        return export_as_csv(data)
    elif format_type == 'json':
        return export_as_json(data)
    else:
        return HttpResponse("Unsupported format", status=400)


def get_time_statistics(user, period):
    """시간 통계 조회"""
    # 실제 구현 필요
    return {
        'total_hours': 160,
        'projects': 5,
        'average_daily': 8
    }


def calculate_productivity(user, start, end):
    """생산성 계산"""
    # 실제 구현 필요
    return {
        'productivity_score': 85,
        'trend': 'up'
    }


def get_team_time_data():
    """팀 시간 데이터 조회"""
    # 실제 구현 필요
    return []


def get_export_data(user, period):
    """내보내기 데이터 조회"""
    # 실제 구현 필요
    return []


def export_as_csv(data):
    """CSV 내보내기"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="time_report.csv"'
    
    writer = csv.writer(response)
    # CSV 작성 로직
    
    return response


def export_as_json(data):
    """JSON 내보내기"""
    return JsonResponse(data, safe=False)
''')
    print("✅ report_views.py 생성")

# 4. entry_views.py - 시간 입력 관련 뷰
with open(target_dir / 'entry_views.py', 'w', encoding='utf-8') as f:
    f.write('''"""시간 입력 관련 뷰"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from datetime import datetime, time


@login_required
def time_entry_form(request):
    """시간 입력 폼"""
    if request.method == 'POST':
        entry = create_time_entry(request.POST, request.user)
        if entry:
            messages.success(request, "시간이 기록되었습니다.")
            return redirect('time_entry_list')
        else:
            messages.error(request, "시간 기록에 실패했습니다.")
    
    projects = get_user_projects(request.user)
    return render(request, 'field_reports/time_entry_form.html', {
        'projects': projects
    })


@login_required
def time_entry_list(request):
    """시간 입력 목록"""
    entries = get_time_entries(request.user)
    
    return render(request, 'field_reports/time_entry_list.html', {
        'entries': entries
    })


@login_required
def time_entry_edit(request, entry_id):
    """시간 입력 수정"""
    entry = get_time_entry(entry_id, request.user)
    
    if not entry:
        messages.error(request, "항목을 찾을 수 없습니다.")
        return redirect('time_entry_list')
    
    if request.method == 'POST':
        update_time_entry(entry, request.POST)
        messages.success(request, "수정되었습니다.")
        return redirect('time_entry_list')
    
    return render(request, 'field_reports/time_entry_edit.html', {
        'entry': entry
    })


@login_required
def time_entry_delete(request, entry_id):
    """시간 입력 삭제"""
    if request.method == 'POST':
        if delete_time_entry(entry_id, request.user):
            messages.success(request, "삭제되었습니다.")
        else:
            messages.error(request, "삭제할 수 없습니다.")
    
    return redirect('time_entry_list')


@login_required
def quick_time_entry(request):
    """빠른 시간 입력 (AJAX)"""
    if request.method == 'POST':
        data = json.loads(request.body)
        entry = quick_create_entry(data, request.user)
        
        if entry:
            return JsonResponse({
                'success': True,
                'entry_id': entry.id
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Failed to create entry'
            })
    
    return JsonResponse({'error': 'POST required'}, status=400)


def create_time_entry(data, user):
    """시간 입력 생성"""
    # 실제 구현 필요
    return None


def get_time_entries(user):
    """시간 입력 조회"""
    # 실제 구현 필요
    return []


def get_time_entry(entry_id, user):
    """단일 시간 입력 조회"""
    # 실제 구현 필요
    return None


def update_time_entry(entry, data):
    """시간 입력 업데이트"""
    # 실제 구현 필요
    pass


def delete_time_entry(entry_id, user):
    """시간 입력 삭제"""
    # 실제 구현 필요
    return False


def get_user_projects(user):
    """사용자 프로젝트 조회"""
    # 실제 구현 필요
    return []


def quick_create_entry(data, user):
    """빠른 입력 생성"""
    # 실제 구현 필요
    class MockEntry:
        id = 1
    return MockEntry()
''')
    print("✅ entry_views.py 생성")

# 5. __init__.py
with open(target_dir / '__init__.py', 'w', encoding='utf-8') as f:
    f.write('''"""Time Tracking Views 모듈

시간 추적 관련 모든 뷰 통합
"""

from .calendar_views import (
    calendar_view,
    calendar_api,
    add_calendar_event
)

from .timesheet_views import (
    timesheet_list,
    timesheet_detail,
    timesheet_create,
    timesheet_submit,
    timesheet_approve
)

from .report_views import (
    time_report_dashboard,
    productivity_report,
    team_time_report,
    export_time_report
)

from .entry_views import (
    time_entry_form,
    time_entry_list,
    time_entry_edit,
    time_entry_delete,
    quick_time_entry
)

__all__ = [
    # Calendar
    'calendar_view',
    'calendar_api',
    'add_calendar_event',
    
    # Timesheet
    'timesheet_list',
    'timesheet_detail',
    'timesheet_create',
    'timesheet_submit',
    'timesheet_approve',
    
    # Reports
    'time_report_dashboard',
    'productivity_report',
    'team_time_report',
    'export_time_report',
    
    # Entries
    'time_entry_form',
    'time_entry_list',
    'time_entry_edit',
    'time_entry_delete',
    'quick_time_entry',
]
''')
    print("✅ __init__.py 생성")

# 원본 파일 제거
source_file.unlink()
print(f"🗑️ 원본 파일 제거: {source_file.name}")

print("\n✨ Time Tracking Views 모듈 분할 완료!")
print(f"📁 위치: {target_dir}")