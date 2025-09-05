"""
OneSquare 통합 캘린더 시스템 - Views
FullCalendar 기반 일정 관리 및 권한별 접근 제어
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q, Count, Prefetch
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import json
from datetime import datetime, timedelta

from apps.auth_system.decorators import permission_required
from apps.auth_system.models import CustomUser
from .models import (
    CalendarEvent, CalendarCategory, EventAttendee, 
    CalendarSettings, EventReminder, NotionCalendarSync
)
from .forms import (
    CalendarEventForm, QuickEventForm, EventAttendeeResponseForm,
    CalendarSettingsForm, CalendarFilterForm, EventSearchForm
)


@login_required
def calendar_dashboard(request):
    """캘린더 메인 대시보드"""
    
    # 사용자 설정 가져오기 또는 생성
    calendar_settings, created = CalendarSettings.objects.get_or_create(
        user=request.user,
        defaults={
            'default_view': CalendarSettings.View.MONTH,
            'default_reminder_minutes': 15,
        }
    )
    
    # 기본 컨텍스트
    context = {
        'calendar_settings': calendar_settings,
        'categories': CalendarCategory.objects.filter(
            is_active=True
        ).filter(
            Q(accessible_user_types__isnull=True) |
            Q(accessible_user_types__contains=[request.user.user_type])
        ),
        'today': timezone.now().date(),
        'user': request.user,
    }
    
    return render(request, 'calendar_system/dashboard.html', context)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calendar_events_api(request):
    """캘린더 이벤트 API - FullCalendar용"""
    
    # 날짜 범위 파라미터
    start_date = request.GET.get('start')
    end_date = request.GET.get('end')
    
    # 기본 쿼리셋
    queryset = CalendarEvent.objects.filter(is_active=True)
    
    # 사용자 권한에 따른 필터링
    if request.user.user_type in ['SUPER_ADMIN', 'MANAGER']:
        # 관리자는 모든 이벤트 조회 가능
        pass
    elif request.user.user_type == 'TEAM_MEMBER':
        # 팀원은 자신이 관련된 이벤트만
        queryset = queryset.filter(
            Q(creator=request.user) |
            Q(attendees=request.user)
        ).distinct()
    else:
        # 파트너/도급사는 자신의 이벤트만
        queryset = queryset.filter(creator=request.user)
    
    # 날짜 범위 필터링
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            queryset = queryset.filter(end_datetime__gte=start_dt)
        except ValueError:
            pass
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            queryset = queryset.filter(start_datetime__lte=end_dt)
        except ValueError:
            pass
    
    # 관련 데이터 최적화
    queryset = queryset.select_related('creator', 'category').prefetch_related(
        'attendees'
    ).order_by('start_datetime')
    
    # FullCalendar 형식으로 변환
    events = []
    for event in queryset:
        if event.can_view(request.user):
            events.append(event.fullcalendar_format)
    
    return Response(events)


@login_required
def create_event(request):
    """이벤트 생성"""
    
    if request.method == 'POST':
        form = CalendarEventForm(request.POST, user=request.user)
        if form.is_valid():
            event = form.save()
            messages.success(request, f'이벤트 "{event.title}"가 생성되었습니다.')
            
            # AJAX 요청인 경우 JSON 응답
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'event': event.fullcalendar_format,
                    'message': f'이벤트 "{event.title}"가 생성되었습니다.'
                })
            
            return redirect('calendar_system:dashboard')
    else:
        # URL 파라미터로 초기값 설정
        initial_data = {}
        if request.GET.get('start'):
            initial_data['start_datetime'] = request.GET.get('start')
        if request.GET.get('end'):
            initial_data['end_datetime'] = request.GET.get('end')
        if request.GET.get('title'):
            initial_data['title'] = request.GET.get('title')
        
        form = CalendarEventForm(initial=initial_data, user=request.user)
    
    context = {
        'form': form,
        'title': '새 이벤트 만들기',
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'calendar_system/event_form_modal.html', context)
    
    return render(request, 'calendar_system/event_form.html', context)


@login_required
def edit_event(request, event_id):
    """이벤트 수정"""
    
    event = get_object_or_404(CalendarEvent, id=event_id, is_active=True)
    
    # 권한 확인
    if not event.can_edit(request.user):
        messages.error(request, '이벤트를 수정할 권한이 없습니다.')
        return redirect('calendar_system:dashboard')
    
    if request.method == 'POST':
        form = CalendarEventForm(request.POST, instance=event, user=request.user)
        if form.is_valid():
            updated_event = form.save()
            messages.success(request, f'이벤트 "{updated_event.title}"가 수정되었습니다.')
            
            # AJAX 요청인 경우 JSON 응답
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'event': updated_event.fullcalendar_format,
                    'message': f'이벤트 "{updated_event.title}"가 수정되었습니다.'
                })
            
            return redirect('calendar_system:dashboard')
    else:
        form = CalendarEventForm(instance=event, user=request.user)
    
    context = {
        'form': form,
        'event': event,
        'title': f'이벤트 수정: {event.title}',
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'calendar_system/event_form_modal.html', context)
    
    return render(request, 'calendar_system/event_form.html', context)


@login_required
@require_http_methods(["DELETE"])
def delete_event(request, event_id):
    """이벤트 삭제"""
    
    event = get_object_or_404(CalendarEvent, id=event_id, is_active=True)
    
    # 권한 확인
    if not event.can_edit(request.user):
        return JsonResponse({
            'success': False,
            'message': '이벤트를 삭제할 권한이 없습니다.'
        }, status=403)
    
    event_title = event.title
    event.is_active = False
    event.save()
    
    return JsonResponse({
        'success': True,
        'message': f'이벤트 "{event_title}"가 삭제되었습니다.'
    })


@login_required
def event_detail(request, event_id):
    """이벤트 상세 보기"""
    
    event = get_object_or_404(CalendarEvent, id=event_id, is_active=True)
    
    # 권한 확인
    if not event.can_view(request.user):
        messages.error(request, '이벤트를 조회할 권한이 없습니다.')
        return redirect('calendar_system:dashboard')
    
    # 참석자 정보
    attendees = EventAttendee.objects.filter(event=event).select_related('user')
    user_attendee = attendees.filter(user=request.user).first()
    
    context = {
        'event': event,
        'attendees': attendees,
        'user_attendee': user_attendee,
        'can_edit': event.can_edit(request.user),
        'can_respond': user_attendee is not None,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'calendar_system/event_detail_modal.html', context)
    
    return render(request, 'calendar_system/event_detail.html', context)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def quick_create_event(request):
    """빠른 이벤트 생성 (AJAX)"""
    
    try:
        data = json.loads(request.body)
        
        # 기본 유효성 검사
        if not data.get('title'):
            return JsonResponse({
                'success': False,
                'message': '이벤트 제목은 필수입니다.'
            }, status=400)
        
        # 이벤트 생성
        event = CalendarEvent.objects.create(
            title=data['title'],
            start_datetime=datetime.fromisoformat(data['start_datetime'].replace('Z', '+00:00')),
            end_datetime=datetime.fromisoformat(data['end_datetime'].replace('Z', '+00:00')),
            is_all_day=data.get('is_all_day', False),
            creator=request.user,
            event_type=CalendarEvent.EventType.WORK,
            priority=CalendarEvent.Priority.MEDIUM,
        )
        
        # 작성자를 참석자로 추가
        EventAttendee.objects.create(
            event=event,
            user=request.user,
            status=EventAttendee.Status.ACCEPTED
        )
        
        return JsonResponse({
            'success': True,
            'event': event.fullcalendar_format,
            'message': f'이벤트 "{event.title}"가 생성되었습니다.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'이벤트 생성 중 오류가 발생했습니다: {str(e)}'
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def update_event_time(request, event_id):
    """이벤트 시간 수정 (드래그 앤 드롭)"""
    
    event = get_object_or_404(CalendarEvent, id=event_id, is_active=True)
    
    # 권한 확인
    if not event.can_edit(request.user):
        return JsonResponse({
            'success': False,
            'message': '이벤트를 수정할 권한이 없습니다.'
        }, status=403)
    
    try:
        data = json.loads(request.body)
        
        # 날짜/시간 업데이트
        if 'start_datetime' in data:
            event.start_datetime = datetime.fromisoformat(data['start_datetime'].replace('Z', '+00:00'))
        
        if 'end_datetime' in data:
            event.end_datetime = datetime.fromisoformat(data['end_datetime'].replace('Z', '+00:00'))
        
        # 유효성 검사
        if event.end_datetime <= event.start_datetime:
            return JsonResponse({
                'success': False,
                'message': '종료일시는 시작일시보다 늦어야 합니다.'
            }, status=400)
        
        event.save()
        
        return JsonResponse({
            'success': True,
            'event': event.fullcalendar_format,
            'message': f'이벤트 "{event.title}" 시간이 수정되었습니다.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'시간 수정 중 오류가 발생했습니다: {str(e)}'
        }, status=500)


@login_required
def respond_to_event(request, event_id):
    """이벤트 참석 응답"""
    
    event = get_object_or_404(CalendarEvent, id=event_id, is_active=True)
    attendee = get_object_or_404(EventAttendee, event=event, user=request.user)
    
    if request.method == 'POST':
        form = EventAttendeeResponseForm(request.POST, instance=attendee)
        if form.is_valid():
            form.save()
            
            status_text = attendee.get_status_display()
            messages.success(request, f'"{event.title}" 이벤트에 "{status_text}"으로 응답했습니다.')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'status': attendee.status,
                    'status_display': status_text,
                    'message': f'응답이 저장되었습니다.'
                })
            
            return redirect('calendar_system:event_detail', event_id=event.id)
    else:
        form = EventAttendeeResponseForm(instance=attendee)
    
    context = {
        'form': form,
        'event': event,
        'attendee': attendee,
    }
    
    return render(request, 'calendar_system/attendee_response.html', context)


@login_required
def calendar_settings_view(request):
    """캘린더 설정"""
    
    settings, created = CalendarSettings.objects.get_or_create(
        user=request.user,
        defaults={
            'default_view': CalendarSettings.View.MONTH,
            'default_reminder_minutes': 15,
        }
    )
    
    if request.method == 'POST':
        form = CalendarSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, '캘린더 설정이 저장되었습니다.')
            return redirect('calendar_system:settings')
    else:
        form = CalendarSettingsForm(instance=settings)
    
    context = {
        'form': form,
        'settings': settings,
    }
    
    return render(request, 'calendar_system/settings.html', context)


@login_required
def my_events(request):
    """내 이벤트 목록"""
    
    # 검색 및 필터 폼
    filter_form = CalendarFilterForm(request.GET, user=request.user)
    search_form = EventSearchForm(request.GET)
    
    # 기본 쿼리셋
    queryset = CalendarEvent.objects.filter(
        Q(creator=request.user) | Q(attendees=request.user),
        is_active=True
    ).distinct().select_related('creator', 'category').prefetch_related('attendees')
    
    # 필터 적용
    if filter_form.is_valid():
        if filter_form.cleaned_data.get('category'):
            queryset = queryset.filter(category=filter_form.cleaned_data['category'])
        
        if filter_form.cleaned_data.get('event_type'):
            queryset = queryset.filter(event_type=filter_form.cleaned_data['event_type'])
        
        if filter_form.cleaned_data.get('priority'):
            queryset = queryset.filter(priority=filter_form.cleaned_data['priority'])
        
        if filter_form.cleaned_data.get('creator'):
            queryset = queryset.filter(creator=filter_form.cleaned_data['creator'])
        
        if filter_form.cleaned_data.get('date_from'):
            queryset = queryset.filter(start_datetime__date__gte=filter_form.cleaned_data['date_from'])
        
        if filter_form.cleaned_data.get('date_to'):
            queryset = queryset.filter(end_datetime__date__lte=filter_form.cleaned_data['date_to'])
    
    # 검색 적용
    if search_form.is_valid() and search_form.cleaned_data.get('query'):
        query = search_form.cleaned_data['query']
        search_type = search_form.cleaned_data.get('search_type', 'all')
        
        if search_type == 'title':
            queryset = queryset.filter(title__icontains=query)
        elif search_type == 'description':
            queryset = queryset.filter(description__icontains=query)
        elif search_type == 'location':
            queryset = queryset.filter(location__icontains=query)
        else:  # all
            queryset = queryset.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(location__icontains=query)
            )
    
    # 정렬
    queryset = queryset.order_by('-start_datetime')
    
    # 페이지네이션
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'filter_form': filter_form,
        'search_form': search_form,
        'total_events': queryset.count(),
    }
    
    return render(request, 'calendar_system/my_events.html', context)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def upcoming_events_api(request):
    """다가오는 이벤트 API (대시보드용)"""
    
    # 오늘부터 7일 후까지의 이벤트
    start_date = timezone.now()
    end_date = start_date + timedelta(days=7)
    
    queryset = CalendarEvent.objects.filter(
        Q(creator=request.user) | Q(attendees=request.user),
        start_datetime__range=[start_date, end_date],
        is_active=True
    ).distinct().order_by('start_datetime')[:10]
    
    events = []
    for event in queryset:
        if event.can_view(request.user):
            events.append({
                'id': event.id,
                'title': event.title,
                'start_datetime': event.start_datetime.isoformat(),
                'end_datetime': event.end_datetime.isoformat(),
                'is_all_day': event.is_all_day,
                'event_type': event.event_type,
                'priority': event.priority,
                'location': event.location,
                'category_name': event.category.name if event.category else '',
                'category_color': event.category.color if event.category else '#3788d8',
                'can_edit': event.can_edit(request.user),
            })
    
    return Response(events)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calendar_stats_api(request):
    """캘린더 통계 API"""
    
    # 현재 월의 통계
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
    
    # 사용자별 이벤트 쿼리셋
    user_events = CalendarEvent.objects.filter(
        Q(creator=request.user) | Q(attendees=request.user),
        is_active=True
    ).distinct()
    
    stats = {
        'total_events': user_events.count(),
        'this_month_events': user_events.filter(
            start_datetime__range=[month_start, month_end]
        ).count(),
        'upcoming_events': user_events.filter(
            start_datetime__gt=now
        ).count(),
        'pending_responses': EventAttendee.objects.filter(
            user=request.user,
            status=EventAttendee.Status.PENDING,
            event__start_datetime__gt=now,
            event__is_active=True
        ).count(),
    }
    
    # 이벤트 타입별 분포
    event_types = user_events.values('event_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # 우선순위별 분포
    priorities = user_events.values('priority').annotate(
        count=Count('id')
    ).order_by('-count')
    
    return Response({
        'stats': stats,
        'event_types': list(event_types),
        'priorities': list(priorities),
    })


# 레거시 API (호환성 유지)
@api_view(['GET'])
def calendar_status(request):
    """Calendar system status check"""
    return Response({
        'message': 'Calendar system is ready',
        'status': 'success',
        'features': {
            'fullcalendar': True,
            'notion_sync': True,
            'permissions': True,
            'pwa_support': True,
        }
    })