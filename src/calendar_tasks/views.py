"""캘린더 태스크 뷰"""
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q, Prefetch, Count
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from datetime import datetime, timedelta, date
import json
import calendar as cal
import logging

from .models import (
    Calendar, Event, RecurringEvent, Task, 
    EventReminder, CalendarShare
)

logger = logging.getLogger(__name__)


class CalendarListView(LoginRequiredMixin, ListView):
    """캘린더 목록 뷰"""
    model = Calendar
    template_name = 'calendar_tasks/calendar_list.html'
    context_object_name = 'calendars'
    
    def get_queryset(self):
        user = self.request.user
        return Calendar.objects.filter(
            Q(owner=user) | Q(shared_with=user)
        ).distinct()


class CalendarDetailView(LoginRequiredMixin, DetailView):
    """캘린더 상세 뷰"""
    model = Calendar
    template_name = 'calendar_tasks/calendar_detail.html'
    context_object_name = 'calendar'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        calendar = self.object
        
        # 날짜 범위 파라미터
        start_date = self.request.GET.get('start')
        end_date = self.request.GET.get('end')
        
        if start_date:
            start_date = datetime.fromisoformat(start_date)
        else:
            start_date = timezone.now().replace(day=1, hour=0, minute=0, second=0)
        
        if end_date:
            end_date = datetime.fromisoformat(end_date)
        else:
            # 기본적으로 현재 월의 마지막 날
            next_month = start_date.replace(day=28) + timedelta(days=4)
            end_date = next_month - timedelta(days=next_month.day)
        
        # 이벤트 조회
        events = calendar.events.filter(
            start_date__lte=end_date,
            end_date__gte=start_date
        )
        
        context['events'] = events
        context['start_date'] = start_date
        context['end_date'] = end_date
        
        return context


class EventCreateView(LoginRequiredMixin, CreateView):
    """이벤트 생성 뷰"""
    model = Event
    template_name = 'calendar_tasks/event_form.html'
    fields = [
        'title', 'description', 'location', 'start_date', 'end_date',
        'all_day', 'is_task', 'priority', 'category', 'tags', 
        'reminder_minutes', 'attendees', 'meeting_link'
    ]
    
    def form_valid(self, form):
        form.instance.creator = self.request.user
        form.instance.calendar_id = self.kwargs.get('calendar_id')
        return super().form_valid(form)
    
    def get_success_url(self):
        return f"/calendar/{self.object.calendar.id}/"


class EventDetailView(LoginRequiredMixin, DetailView):
    """이벤트 상세 뷰"""
    model = Event
    template_name = 'calendar_tasks/event_detail.html'
    context_object_name = 'event'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.object
        
        # 태스크 정보
        if event.is_task:
            try:
                context['task'] = event.task_detail
            except Task.DoesNotExist:
                context['task'] = None
        
        # 반복 설정
        try:
            context['recurrence'] = event.recurrence
        except RecurringEvent.DoesNotExist:
            context['recurrence'] = None
        
        # 알림 설정
        context['reminders'] = event.reminders.filter(user=self.request.user)
        
        return context


class EventUpdateView(LoginRequiredMixin, UpdateView):
    """이벤트 수정 뷰"""
    model = Event
    template_name = 'calendar_tasks/event_form.html'
    fields = [
        'title', 'description', 'location', 'start_date', 'end_date',
        'all_day', 'is_task', 'priority', 'status', 'progress',
        'category', 'tags', 'reminder_minutes', 'attendees', 'meeting_link'
    ]
    
    def get_queryset(self):
        # 편집 권한 확인
        return Event.objects.filter(
            Q(creator=self.request.user) |
            Q(calendar__owner=self.request.user) |
            Q(calendar__shared_with=self.request.user, 
              calendar__share_permission__in=['edit', 'admin'])
        )
    
    def get_success_url(self):
        return f"/event/{self.object.id}/"


# API Views
@login_required
def api_calendar_events(request, calendar_id):
    """캘린더 이벤트 API"""
    calendar = get_object_or_404(Calendar, id=calendar_id)
    
    # 권한 확인
    if not (calendar.owner == request.user or request.user in calendar.shared_with.all()):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # 날짜 범위
    start = request.GET.get('start')
    end = request.GET.get('end')
    
    events_query = calendar.events.all()
    
    if start:
        events_query = events_query.filter(end_date__gte=start)
    if end:
        events_query = events_query.filter(start_date__lte=end)
    
    # 이벤트 데이터 포맷팅
    events_data = []
    for event in events_query:
        event_dict = {
            'id': event.id,
            'title': event.title,
            'start': event.start_date.isoformat(),
            'end': event.end_date.isoformat(),
            'allDay': event.all_day,
            'color': event.get_color(),
            'description': event.description,
            'location': event.location,
            'isTask': event.is_task,
            'status': event.status,
            'priority': event.priority,
            'progress': event.progress if event.is_task else None,
        }
        
        # 반복 이벤트 처리
        try:
            recurrence = event.recurrence
            if recurrence:
                # 반복 인스턴스 생성
                occurrences = recurrence.generate_occurrences(
                    datetime.fromisoformat(start) if start else None,
                    datetime.fromisoformat(end) if end else None
                )
                
                for occurrence in occurrences[1:]:  # 첫 번째는 이미 포함됨
                    recurring_event = event_dict.copy()
                    recurring_event['id'] = f"{event.id}_r_{occurrence.isoformat()}"
                    recurring_event['start'] = occurrence.isoformat()
                    duration = event.end_date - event.start_date
                    recurring_event['end'] = (occurrence + duration).isoformat()
                    recurring_event['recurring'] = True
                    events_data.append(recurring_event)
        except RecurringEvent.DoesNotExist:
            pass
        
        events_data.append(event_dict)
    
    return JsonResponse({'events': events_data})


@login_required
def api_create_event(request):
    """이벤트 생성 API"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    data = json.loads(request.body)
    
    # 캘린더 권한 확인
    calendar = get_object_or_404(Calendar, id=data['calendar_id'])
    if not calendar.can_user_edit(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    # 이벤트 생성
    event = Event.objects.create(
        calendar=calendar,
        creator=request.user,
        title=data['title'],
        description=data.get('description', ''),
        location=data.get('location', ''),
        start_date=datetime.fromisoformat(data['start']),
        end_date=datetime.fromisoformat(data['end']),
        all_day=data.get('allDay', False),
        is_task=data.get('isTask', False),
        priority=data.get('priority', 'medium'),
        status=data.get('status', 'scheduled'),
        category=data.get('category', ''),
        tags=data.get('tags', []),
        color=data.get('color', ''),
        reminder_minutes=data.get('reminderMinutes'),
        meeting_link=data.get('meetingLink', '')
    )
    
    # 참석자 추가
    if 'attendees' in data:
        event.attendees.set(data['attendees'])
    
    # 태스크 생성
    if event.is_task and data.get('checklist'):
        Task.objects.create(
            event=event,
            checklist=data['checklist'],
            estimated_minutes=data.get('estimatedMinutes')
        )
    
    # 반복 설정
    if data.get('recurring'):
        RecurringEvent.objects.create(
            event=event,
            frequency=data['recurring']['frequency'],
            interval=data['recurring'].get('interval', 1),
            weekdays=data['recurring'].get('weekdays', []),
            month_day=data['recurring'].get('monthDay'),
            month_week=data['recurring'].get('monthWeek'),
            end_type=data['recurring'].get('endType', 'never'),
            occurrences=data['recurring'].get('occurrences'),
            end_date=datetime.fromisoformat(data['recurring']['endDate']) 
                     if data['recurring'].get('endDate') else None
        )
    
    # 알림 설정
    if event.reminder_minutes:
        remind_at = event.start_date - timedelta(minutes=event.reminder_minutes)
        EventReminder.objects.create(
            event=event,
            user=request.user,
            remind_at=remind_at,
            message=f"알림: {event.title}이(가) {event.reminder_minutes}분 후 시작됩니다."
        )
    
    return JsonResponse({
        'success': True,
        'event_id': event.id
    })


@login_required
def api_update_event(request, event_id):
    """이벤트 수정 API"""
    if request.method != 'PUT':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    event = get_object_or_404(Event, id=event_id)
    
    # 권한 확인
    if not event.calendar.can_user_edit(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    data = json.loads(request.body)
    
    # 이벤트 업데이트
    for field in ['title', 'description', 'location', 'category', 'meeting_link']:
        if field in data:
            setattr(event, field, data[field])
    
    if 'start' in data:
        event.start_date = datetime.fromisoformat(data['start'])
    if 'end' in data:
        event.end_date = datetime.fromisoformat(data['end'])
    if 'allDay' in data:
        event.all_day = data['allDay']
    if 'priority' in data:
        event.priority = data['priority']
    if 'status' in data:
        event.status = data['status']
    if 'progress' in data:
        event.progress = data['progress']
    if 'tags' in data:
        event.tags = data['tags']
    if 'color' in data:
        event.color = data['color']
    
    event.save()
    
    # 태스크 업데이트
    if event.is_task and data.get('checklist'):
        task, created = Task.objects.get_or_create(event=event)
        task.checklist = data['checklist']
        task.save()
        task.update_event_progress()
    
    return JsonResponse({'success': True})


@login_required
def api_delete_event(request, event_id):
    """이벤트 삭제 API"""
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    event = get_object_or_404(Event, id=event_id)
    
    # 권한 확인
    if not (event.creator == request.user or 
            event.calendar.owner == request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    event.delete()
    
    return JsonResponse({'success': True})


@login_required
def api_task_checklist(request, task_id):
    """태스크 체크리스트 API"""
    task = get_object_or_404(Task, id=task_id)
    
    if request.method == 'GET':
        return JsonResponse({
            'checklist': task.checklist,
            'progress': task.get_checklist_progress()
        })
    
    elif request.method == 'PUT':
        # 권한 확인
        if not task.event.calendar.can_user_edit(request.user):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        data = json.loads(request.body)
        task.checklist = data['checklist']
        task.save()
        task.update_event_progress()
        
        return JsonResponse({
            'success': True,
            'progress': task.get_checklist_progress()
        })
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def api_upcoming_events(request):
    """다가오는 이벤트 API"""
    user = request.user
    days = int(request.GET.get('days', 7))
    
    # 사용자가 접근 가능한 캘린더
    calendars = Calendar.objects.filter(
        Q(owner=user) | Q(shared_with=user)
    ).distinct()
    
    # 다가오는 이벤트
    end_date = timezone.now() + timedelta(days=days)
    events = Event.objects.filter(
        calendar__in=calendars,
        start_date__gte=timezone.now(),
        start_date__lte=end_date
    ).order_by('start_date')[:20]
    
    events_data = [{
        'id': event.id,
        'title': event.title,
        'start': event.start_date.isoformat(),
        'end': event.end_date.isoformat(),
        'calendar': event.calendar.name,
        'calendarColor': event.calendar.color,
        'isTask': event.is_task,
        'status': event.status,
        'priority': event.priority,
        'isOverdue': event.is_overdue()
    } for event in events]
    
    return JsonResponse({'events': events_data})


@login_required
def api_overdue_tasks(request):
    """기한 초과 태스크 API"""
    user = request.user
    
    # 사용자가 접근 가능한 캘린더
    calendars = Calendar.objects.filter(
        Q(owner=user) | Q(shared_with=user)
    ).distinct()
    
    # 기한 초과 태스크
    overdue_tasks = Event.objects.filter(
        calendar__in=calendars,
        is_task=True,
        status__in=['scheduled', 'in_progress'],
        end_date__lt=timezone.now()
    ).order_by('priority', 'end_date')
    
    tasks_data = [{
        'id': task.id,
        'title': task.title,
        'dueDate': task.end_date.isoformat(),
        'calendar': task.calendar.name,
        'priority': task.priority,
        'progress': task.progress,
        'daysOverdue': (timezone.now() - task.end_date).days
    } for task in overdue_tasks]
    
    return JsonResponse({'tasks': tasks_data})


class WeeklyCalendarView(LoginRequiredMixin, View):
    """최적화된 주간 캘린더 뷰"""
    
    def get(self, request):
        """주간 캘린더 데이터 조회"""
        try:
            # 날짜 파라미터 처리
            date_str = request.GET.get('date')
            if date_str:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            else:
                target_date = date.today()
            
            # 주의 시작과 끝 계산 (월요일 시작)
            week_start = target_date - timedelta(days=target_date.weekday())
            week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
            
            # 캐시 키 생성
            cache_key = f'weekly_calendar_{request.user.id}_{week_start.strftime("%Y%m%d")}'
            cached_data = cache.get(cache_key)
            
            if cached_data:
                logger.info(f"Weekly calendar cache hit for user {request.user.id}")
                return JsonResponse(cached_data)
            
            # 캘린더 조회 (최적화된 쿼리)
            user_calendars = Calendar.objects.filter(
                Q(owner=request.user) | Q(shared_with=request.user)
            ).distinct().prefetch_related(
                Prefetch('events', 
                    queryset=Event.objects.filter(
                        Q(start_date__lte=week_end) & Q(end_date__gte=week_start)
                    ).select_related('calendar', 'creator')
                    .prefetch_related('attendees', 'reminders', 'task_detail')
                )
            )
            
            # 주간 데이터 구성
            week_data = {
                'week_start': week_start.isoformat(),
                'week_end': week_end.isoformat(),
                'days': []
            }
            
            # 각 날짜별 이벤트 정리
            for i in range(7):
                current_date = week_start + timedelta(days=i)
                day_events = []
                
                for calendar in user_calendars:
                    for event in calendar.events.all():
                        # 이벤트가 해당 날짜에 포함되는지 확인
                        if event.start_date.date() <= current_date <= event.end_date.date():
                            event_data = {
                                'id': event.id,
                                'title': event.title,
                                'start': event.start_date.isoformat(),
                                'end': event.end_date.isoformat(),
                                'all_day': event.all_day,
                                'calendar': {
                                    'id': calendar.id,
                                    'name': calendar.name,
                                    'color': calendar.color
                                },
                                'is_task': event.is_task,
                                'status': event.status,
                                'priority': event.priority
                            }
                            
                            # 태스크 정보 추가
                            if event.is_task:
                                try:
                                    task = event.task_detail
                                    event_data['progress'] = task.get_checklist_progress()
                                except Task.DoesNotExist:
                                    event_data['progress'] = 0
                            
                            day_events.append(event_data)
                
                # 반복 이벤트 처리
                recurring_events = RecurringEvent.objects.filter(
                    event__calendar__in=user_calendars
                ).select_related('event', 'event__calendar')
                
                for recurrence in recurring_events:
                    occurrences = recurrence.generate_occurrences(
                        start_date=timezone.make_aware(datetime.combine(current_date, datetime.min.time())),
                        end_date=timezone.make_aware(datetime.combine(current_date, datetime.max.time()))
                    )
                    
                    for occurrence in occurrences:
                        if occurrence.date() == current_date:
                            event = recurrence.event
                            day_events.append({
                                'id': f"{event.id}_r_{occurrence.isoformat()}",
                                'title': event.title,
                                'start': occurrence.isoformat(),
                                'end': (occurrence + event.get_duration()).isoformat(),
                                'all_day': event.all_day,
                                'calendar': {
                                    'id': event.calendar.id,
                                    'name': event.calendar.name,
                                    'color': event.calendar.color
                                },
                                'is_recurring': True,
                                'is_task': event.is_task,
                                'status': event.status
                            })
                
                week_data['days'].append({
                    'date': current_date.isoformat(),
                    'day_name': current_date.strftime('%A'),
                    'day_number': current_date.day,
                    'is_today': current_date == date.today(),
                    'events': sorted(day_events, key=lambda x: x['start'])
                })
            
            # 통계 정보 추가
            total_events = sum(len(day['events']) for day in week_data['days'])
            task_count = sum(
                len([e for e in day['events'] if e.get('is_task')])
                for day in week_data['days']
            )
            
            week_data['statistics'] = {
                'total_events': total_events,
                'total_tasks': task_count,
                'calendars_count': user_calendars.count()
            }
            
            # 캐시 저장 (10분)
            cache.set(cache_key, week_data, 600)
            logger.info(f"Weekly calendar cached for user {request.user.id}")
            
            return JsonResponse(week_data)
            
        except Exception as e:
            logger.error(f"Weekly calendar error for user {request.user.id}: {str(e)}")
            return JsonResponse({
                'error': '주간 캘린더 로드 중 오류가 발생했습니다.',
                'detail': str(e)
            }, status=500)


class DailyCalendarView(LoginRequiredMixin, View):
    """최적화된 일간 캘린더 뷰"""
    
    def get(self, request):
        """일간 캘린더 데이터 조회"""
        try:
            # 날짜 파라미터 처리
            date_str = request.GET.get('date')
            if date_str:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            else:
                target_date = date.today()
            
            # 시간대 설정
            day_start = timezone.make_aware(datetime.combine(target_date, datetime.min.time()))
            day_end = timezone.make_aware(datetime.combine(target_date, datetime.max.time()))
            
            # 캐시 키 생성
            cache_key = f'daily_calendar_{request.user.id}_{target_date.strftime("%Y%m%d")}'
            cached_data = cache.get(cache_key)
            
            if cached_data:
                logger.info(f"Daily calendar cache hit for user {request.user.id}")
                return JsonResponse(cached_data)
            
            # 사용자 캘린더 조회
            user_calendars = Calendar.objects.filter(
                Q(owner=request.user) | Q(shared_with=request.user)
            ).distinct()
            
            # 해당 날짜의 이벤트 조회 (최적화)
            events = Event.objects.filter(
                calendar__in=user_calendars,
                start_date__lte=day_end,
                end_date__gte=day_start
            ).select_related(
                'calendar', 'creator'
            ).prefetch_related(
                'attendees', 'reminders', 'task_detail'
            ).order_by('start_date')
            
            # 시간별 슬롯 생성 (24시간)
            time_slots = {}
            for hour in range(24):
                time_slots[hour] = []
            
            # 이벤트를 시간별로 분류
            all_day_events = []
            
            for event in events:
                event_data = {
                    'id': event.id,
                    'title': event.title,
                    'description': event.description,
                    'location': event.location,
                    'start': event.start_date.isoformat(),
                    'end': event.end_date.isoformat(),
                    'all_day': event.all_day,
                    'calendar': {
                        'id': event.calendar.id,
                        'name': event.calendar.name,
                        'color': event.calendar.color
                    },
                    'is_task': event.is_task,
                    'status': event.status,
                    'priority': event.priority,
                    'creator': event.creator.username,
                    'attendees': [u.username for u in event.attendees.all()]
                }
                
                # 태스크 진행률
                if event.is_task:
                    try:
                        task = event.task_detail
                        event_data['progress'] = task.get_checklist_progress()
                        event_data['checklist'] = task.checklist
                    except Task.DoesNotExist:
                        event_data['progress'] = 0
                
                # 알림 정보
                user_reminders = event.reminders.filter(user=request.user, is_sent=False)
                if user_reminders.exists():
                    event_data['next_reminder'] = user_reminders.first().remind_at.isoformat()
                
                # 종일 이벤트 분류
                if event.all_day:
                    all_day_events.append(event_data)
                else:
                    # 시간별 슬롯에 배치
                    start_hour = event.start_date.hour
                    end_hour = event.end_date.hour if event.end_date.date() == target_date else 23
                    
                    for hour in range(start_hour, min(end_hour + 1, 24)):
                        time_slots[hour].append(event_data)
            
            # 반복 이벤트 처리
            recurring_events = RecurringEvent.objects.filter(
                event__calendar__in=user_calendars
            ).select_related('event', 'event__calendar')
            
            for recurrence in recurring_events:
                occurrences = recurrence.generate_occurrences(day_start, day_end)
                
                for occurrence in occurrences:
                    if occurrence.date() == target_date:
                        event = recurrence.event
                        duration = event.get_duration()
                        
                        recurring_data = {
                            'id': f"{event.id}_r_{occurrence.isoformat()}",
                            'title': event.title,
                            'description': event.description,
                            'start': occurrence.isoformat(),
                            'end': (occurrence + duration).isoformat(),
                            'all_day': event.all_day,
                            'calendar': {
                                'id': event.calendar.id,
                                'name': event.calendar.name,
                                'color': event.calendar.color
                            },
                            'is_recurring': True,
                            'is_task': event.is_task,
                            'status': event.status,
                            'priority': event.priority
                        }
                        
                        if event.all_day:
                            all_day_events.append(recurring_data)
                        else:
                            start_hour = occurrence.hour
                            end_hour = min((occurrence + duration).hour, 23)
                            for hour in range(start_hour, end_hour + 1):
                                time_slots[hour].append(recurring_data)
            
            # 시간별 슬롯 정리
            formatted_slots = []
            for hour in range(24):
                formatted_slots.append({
                    'hour': hour,
                    'time': f"{hour:02d}:00",
                    'events': time_slots[hour]
                })
            
            # 일간 데이터 구성
            daily_data = {
                'date': target_date.isoformat(),
                'day_name': target_date.strftime('%A'),
                'is_today': target_date == date.today(),
                'all_day_events': all_day_events,
                'time_slots': formatted_slots,
                'statistics': {
                    'total_events': len(events) + len(all_day_events),
                    'total_tasks': len([e for e in events if e.is_task]),
                    'completed_tasks': len([e for e in events if e.is_task and e.status == 'completed']),
                    'overdue_tasks': len([e for e in events if e.is_task and e.is_overdue()])
                }
            }
            
            # 캐시 저장 (5분)
            cache.set(cache_key, daily_data, 300)
            logger.info(f"Daily calendar cached for user {request.user.id}")
            
            return JsonResponse(daily_data)
            
        except Exception as e:
            logger.error(f"Daily calendar error for user {request.user.id}: {str(e)}")
            return JsonResponse({
                'error': '일간 캘린더 로드 중 오류가 발생했습니다.',
                'detail': str(e)
            }, status=500)


@login_required
@cache_page(60)  # 1분 캐싱
def api_calendar_summary(request):
    """캘린더 요약 정보 API (캐싱 적용)"""
    user = request.user
    
    try:
        # 오늘 날짜
        today = date.today()
        today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
        today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
        
        # 사용자 캘린더
        user_calendars = Calendar.objects.filter(
            Q(owner=user) | Q(shared_with=user)
        ).distinct()
        
        # 오늘의 이벤트
        today_events = Event.objects.filter(
            calendar__in=user_calendars,
            start_date__lte=today_end,
            end_date__gte=today_start
        ).count()
        
        # 이번 주 이벤트
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        week_events = Event.objects.filter(
            calendar__in=user_calendars,
            start_date__date__lte=week_end,
            end_date__date__gte=week_start
        ).count()
        
        # 미완료 태스크
        pending_tasks = Event.objects.filter(
            calendar__in=user_calendars,
            is_task=True,
            status__in=['scheduled', 'in_progress']
        ).count()
        
        # 기한 초과 태스크
        overdue_tasks = Event.objects.filter(
            calendar__in=user_calendars,
            is_task=True,
            status__in=['scheduled', 'in_progress'],
            end_date__lt=timezone.now()
        ).count()
        
        summary = {
            'today': today.isoformat(),
            'calendars_count': user_calendars.count(),
            'today_events': today_events,
            'week_events': week_events,
            'pending_tasks': pending_tasks,
            'overdue_tasks': overdue_tasks,
            'next_event': None
        }
        
        # 다음 이벤트
        next_event = Event.objects.filter(
            calendar__in=user_calendars,
            start_date__gte=timezone.now()
        ).order_by('start_date').first()
        
        if next_event:
            summary['next_event'] = {
                'id': next_event.id,
                'title': next_event.title,
                'start': next_event.start_date.isoformat(),
                'calendar': next_event.calendar.name
            }
        
        return JsonResponse(summary)
        
    except Exception as e:
        logger.error(f"Calendar summary error: {str(e)}")
        return JsonResponse({'error': '요약 정보 로드 실패'}, status=500)
