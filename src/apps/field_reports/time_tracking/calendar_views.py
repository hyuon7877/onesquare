"""캘린더 관련 뷰"""
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
