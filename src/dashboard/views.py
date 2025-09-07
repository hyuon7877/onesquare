from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.db.models import Count, Q, Sum
from field_reports.models import FieldReport
# collaboration 모델 사용 (dashboard 모델 대신)
from collaboration.models import Activity, Notification
from .models import CalendarEvent
import json

@login_required
def dashboard_view(request):
    """메인 대시보드 뷰 - 실시간 통계 포함"""
    
    # 기간별 날짜 계산
    now = timezone.now()
    today = now.date()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # 사용자 통계
    total_users = User.objects.count()
    new_users_week = User.objects.filter(date_joined__gte=week_ago).count()
    new_users_month = User.objects.filter(date_joined__gte=month_ago).count()
    
    # 현장 리포트 통계
    total_reports = FieldReport.objects.count()
    reports_by_status = FieldReport.objects.values('status').annotate(count=Count('id'))
    reports_week = FieldReport.objects.filter(created_at__gte=week_ago).count()
    
    # 활동 통계 (collaboration.Activity 사용)
    recent_activities = Activity.objects.select_related('user').order_by('-created_at')[:5]
    
    # 알림 통계 (collaboration.Notification 사용)
    unread_notifications = Notification.objects.filter(
        recipient=request.user, 
        is_read=False
    ).count()
    
    context = {
        'total_users': total_users,
        'new_users_week': new_users_week,
        'new_users_month': new_users_month,
        'total_reports': total_reports,
        'reports_by_status': reports_by_status,
        'reports_week': reports_week,
        'recent_activities': recent_activities,
        'unread_notifications': unread_notifications,
        'today': today,
        'chart_data': {
            'labels': ['월', '화', '수', '목', '금', '토', '일'],
            'datasets': [
                {
                    'label': '신규 사용자',
                    'data': [12, 19, 3, 5, 2, 3, 7],
                    'borderColor': 'rgb(75, 192, 192)',
                    'tension': 0.1
                },
                {
                    'label': '보고서 제출',
                    'data': [5, 8, 12, 7, 9, 4, 6],
                    'borderColor': 'rgb(255, 99, 132)',
                    'tension': 0.1
                }
            ]
        }
    }
    
    return render(request, 'dashboard/dashboard.html', context)

@login_required
@require_http_methods(["GET"])
def get_statistics(request):
    """대시보드 통계 데이터 API"""
    
    # 실제 데이터베이스에서 통계 가져오기
    total_users = User.objects.count()
    active_users = User.objects.filter(last_login__gte=timezone.now() - timedelta(days=30)).count()
    total_reports = FieldReport.objects.count()
    pending_reports = FieldReport.objects.filter(status='draft').count()
    
    # 월별 사용자 증가 데이터
    user_growth = []
    for i in range(5, 0, -1):
        month_start = timezone.now() - timedelta(days=30*i)
        month_end = timezone.now() - timedelta(days=30*(i-1))
        count = User.objects.filter(date_joined__gte=month_start, date_joined__lt=month_end).count()
        user_growth.append({
            'month': month_start.strftime('%m월'),
            'value': count
        })
    
    stats = {
        'total_users': total_users,
        'active_projects': active_users,  # 활성 사용자로 대체
        'completed_tasks': Activity.objects.filter(activity_type='task_completed').count(),
        'pending_reports': pending_reports,
        'growth_rate': 12.5,  # 예시 성장률
        'user_growth': user_growth
    }
    
    return JsonResponse(stats)

@login_required
@require_http_methods(["GET"])
def get_recent_activities(request):
    """최근 활동 데이터 API"""
    
    # 실제 Activity 모델에서 데이터 가져오기
    recent_activities = Activity.objects.select_related('user').order_by('-created_at')[:10]
    
    activities = []
    for activity in recent_activities:
        activities.append({
            'id': activity.id,
            'type': activity.activity_type,
            'user': activity.user.get_full_name() or activity.user.username,
            'description': activity.get_message() if hasattr(activity, 'get_message') else activity.description,
            'timestamp': activity.created_at.isoformat(),
            'icon': activity.get_icon() if hasattr(activity, 'get_icon') else 'check-circle'
        })
    
    # 활동이 없으면 샘플 데이터 표시
    if not activities:
        activities = [
            {
                'id': 1,
                'type': 'task_completed',
                'user': '시스템',
                'description': '대시보드가 준비되었습니다',
                'timestamp': timezone.now().isoformat(),
                'icon': 'check-circle'
            }
        ]
    
    return JsonResponse({'activities': activities})

@login_required
@require_http_methods(["GET"])
def get_notifications(request):
    """알림 데이터 API"""
    
    # 실제 Notification 모델에서 데이터 가져오기
    user_notifications = Notification.objects.filter(
        recipient=request.user
    ).select_related('sender').order_by('-created_at')[:10]
    
    notifications = []
    for notif in user_notifications:
        notifications.append({
            'id': notif.id,
            'title': notif.title,
            'message': notif.message,
            'unread': not notif.is_read,
            'timestamp': notif.created_at.isoformat(),
        })
    
    # 알림이 없으면 샘플 데이터 표시
    if not notifications:
        notifications = [
            {
                'id': 1,
                'title': '환영합니다',
                'message': 'OneSquare 대시보드에 오신 것을 환영합니다.',
                'unread': True,
                'timestamp': timezone.now().isoformat(),
            }
        ]
    
    unread_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    return JsonResponse({
        'notifications': notifications,
        'unread_count': unread_count
    })

@login_required
@require_http_methods(["GET"])
def get_chart_data(request):
    """차트 데이터 API"""
    chart_type = request.GET.get('type', 'line')
    
    if chart_type == 'line':
        # 라인 차트 데이터
        data = {
            'labels': ['1주', '2주', '3주', '4주', '5주'],
            'datasets': [
                {
                    'label': '작업 완료',
                    'data': [12, 19, 3, 5, 2],
                    'borderColor': 'rgb(75, 192, 192)',
                    'backgroundColor': 'rgba(75, 192, 192, 0.2)',
                },
                {
                    'label': '신규 리포트',
                    'data': [3, 7, 4, 8, 6],
                    'borderColor': 'rgb(255, 99, 132)',
                    'backgroundColor': 'rgba(255, 99, 132, 0.2)',
                }
            ]
        }
    elif chart_type == 'pie':
        # 파이 차트 데이터
        data = {
            'labels': ['완료', '진행중', '대기', '보류'],
            'datasets': [{
                'data': [30, 25, 20, 25],
                'backgroundColor': [
                    'rgb(54, 162, 235)',
                    'rgb(255, 205, 86)',
                    'rgb(75, 192, 192)',
                    'rgb(255, 99, 132)',
                ]
            }]
        }
    else:  # bar
        # 바 차트 데이터
        data = {
            'labels': ['1월', '2월', '3월', '4월', '5월'],
            'datasets': [{
                'label': '월별 실적',
                'data': [65, 59, 80, 81, 56],
                'backgroundColor': 'rgba(54, 162, 235, 0.5)',
            }]
        }
    
    return JsonResponse(data)

@login_required
@require_http_methods(["POST"])
def mark_notification_read(request):
    """알림 읽음 처리 API"""
    try:
        data = json.loads(request.body)
        notification_id = data.get('id')
        
        # 실제 Notification 모델 업데이트
        notification = Notification.objects.get(id=notification_id, recipient=request.user)
        notification.is_read = True
        notification.save()
        
        return JsonResponse({'success': True, 'message': '알림이 읽음 처리되었습니다.'})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': '알림을 찾을 수 없습니다.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
def calendar_view(request):
    """캘린더/일정 관리 페이지"""
    from datetime import datetime, timedelta
    from calendar import monthrange
    
    # 현재 날짜 정보
    today = timezone.now()
    current_year = int(request.GET.get('year', today.year))
    current_month = int(request.GET.get('month', today.month))
    
    # 이번 달의 첫날과 마지막 날
    first_day = datetime(current_year, current_month, 1, tzinfo=timezone.get_current_timezone())
    last_day_num = monthrange(current_year, current_month)[1]
    last_day = datetime(current_year, current_month, last_day_num, 23, 59, 59, tzinfo=timezone.get_current_timezone())
    
    # 이번 달의 이벤트 가져오기
    events = CalendarEvent.objects.filter(
        Q(start_date__gte=first_day, start_date__lte=last_day) |
        Q(end_date__gte=first_day, end_date__lte=last_day) |
        Q(start_date__lte=first_day, end_date__gte=last_day)
    ).select_related('organizer').prefetch_related('participants')
    
    # 이벤트를 날짜별로 그룹화
    events_by_date = {}
    for event in events:
        # 이벤트가 여러 날에 걸쳐있는 경우 처리
        current_date = max(event.start_date.date(), first_day.date())
        end_date = min(event.end_date.date(), last_day.date())
        
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            if date_str not in events_by_date:
                events_by_date[date_str] = []
            
            events_by_date[date_str].append({
                'id': event.id,
                'title': event.title,
                'time': event.start_date.strftime('%H:%M') if current_date == event.start_date.date() else '종일',
                'type': event.event_type,
                'color': event.color,
                'all_day': event.all_day,
            })
            current_date += timedelta(days=1)
    
    # JSON 형식으로 안전하게 변환
    import json
    events_json = json.dumps(events_by_date, ensure_ascii=False)
    
    context = {
        'events_by_date': events_by_date,
        'events_json': events_json,
        'current_month': f"{current_year}년 {current_month}월",
        'current_year': current_year,
        'current_month_num': current_month,
        'today': today.strftime('%Y-%m-%d'),
        'prev_year': current_year if current_month > 1 else current_year - 1,
        'prev_month': current_month - 1 if current_month > 1 else 12,
        'next_year': current_year if current_month < 12 else current_year + 1,
        'next_month': current_month + 1 if current_month < 12 else 1,
    }
    return render(request, 'dashboard/calendar.html', context)

@login_required
def team_management_view(request):
    """팀 관리 페이지"""
    from django.contrib.auth.models import User
    
    # 팀 멤버 목록
    team_members = User.objects.all().select_related('profile') if hasattr(User, 'profile') else User.objects.all()
    
    # 팀 통계
    team_stats = {
        'total_members': team_members.count(),
        'active_members': team_members.filter(is_active=True).count(),
        'departments': [
            {'name': '개발팀', 'count': 5},
            {'name': '기획팀', 'count': 3},
            {'name': '디자인팀', 'count': 2},
            {'name': '마케팅팀', 'count': 2},
        ]
    }
    
    context = {
        'team_members': team_members[:10],  # 처음 10명만 표시
        'team_stats': team_stats,
    }
    return render(request, 'dashboard/team.html', context)


# 캘린더 API 엔드포인트들
@login_required
@require_http_methods(["GET"])
def get_calendar_events(request):
    """캘린더 이벤트 목록 API"""
    year = int(request.GET.get('year', timezone.now().year))
    month = int(request.GET.get('month', timezone.now().month))
    
    from calendar import monthrange
    first_day = datetime(year, month, 1, tzinfo=timezone.get_current_timezone())
    last_day_num = monthrange(year, month)[1]
    last_day = datetime(year, month, last_day_num, 23, 59, 59, tzinfo=timezone.get_current_timezone())
    
    events = CalendarEvent.objects.filter(
        Q(start_date__gte=first_day, start_date__lte=last_day) |
        Q(end_date__gte=first_day, end_date__lte=last_day) |
        Q(start_date__lte=first_day, end_date__gte=last_day)
    ).select_related('organizer').prefetch_related('participants')
    
    events_data = []
    for event in events:
        event_data = {
            'id': event.id,
            'title': event.title,
            'description': event.description,
            'event_type': event.event_type,
            'start_date': event.start_date.isoformat(),
            'end_date': event.end_date.isoformat(),
            'all_day': event.all_day,
            'location': event.location,
            'color': event.color,
            'organizer': {
                'id': event.organizer.id,
                'name': event.organizer.get_full_name() or event.organizer.username
            },
            'participants': [
                {'id': p.id, 'name': p.get_full_name() or p.username}
                for p in event.participants.all()
            ]
        }
        events_data.append(event_data)
    
    return JsonResponse({'events': events_data})


@login_required
@require_http_methods(["POST"])
def create_calendar_event(request):
    """캘린더 이벤트 생성 API"""
    try:
        data = json.loads(request.body)
        
        # 필수 필드 검증
        required_fields = ['title', 'start_date', 'end_date']
        for field in required_fields:
            if field not in data:
                return JsonResponse({'error': f'{field}는 필수 항목입니다.'}, status=400)
        
        # 이벤트 생성
        event = CalendarEvent.objects.create(
            title=data['title'],
            description=data.get('description', ''),
            event_type=data.get('event_type', 'meeting'),
            start_date=timezone.make_aware(datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))),
            end_date=timezone.make_aware(datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))),
            all_day=data.get('all_day', False),
            location=data.get('location', ''),
            color=data.get('color', '#0d6efd'),
            organizer=request.user,
            reminder_minutes=data.get('reminder_minutes', 15),
            is_public=data.get('is_public', True),
            repeat=data.get('repeat', 'none'),
        )
        
        # 참석자 추가
        if 'participants' in data:
            participant_ids = data['participants']
            participants = User.objects.filter(id__in=participant_ids)
            event.participants.set(participants)
        
        # 활동 기록
        Activity.objects.create(
            user=request.user,
            activity_type='event_created',
            description=f"캘린더 이벤트 '{event.title}' 생성"
        )
        
        return JsonResponse({
            'success': True,
            'event': {
                'id': event.id,
                'title': event.title,
                'start_date': event.start_date.isoformat(),
                'end_date': event.end_date.isoformat(),
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["PUT"])
def update_calendar_event(request, event_id):
    """캘린더 이벤트 수정 API"""
    try:
        event = get_object_or_404(CalendarEvent, id=event_id)
        
        # 권한 체크 (주최자만 수정 가능)
        if event.organizer != request.user:
            return JsonResponse({'error': '수정 권한이 없습니다.'}, status=403)
        
        data = json.loads(request.body)
        
        # 필드 업데이트
        if 'title' in data:
            event.title = data['title']
        if 'description' in data:
            event.description = data['description']
        if 'event_type' in data:
            event.event_type = data['event_type']
        if 'start_date' in data:
            event.start_date = timezone.make_aware(datetime.fromisoformat(data['start_date'].replace('Z', '+00:00')))
        if 'end_date' in data:
            event.end_date = timezone.make_aware(datetime.fromisoformat(data['end_date'].replace('Z', '+00:00')))
        if 'all_day' in data:
            event.all_day = data['all_day']
        if 'location' in data:
            event.location = data['location']
        if 'color' in data:
            event.color = data['color']
        if 'reminder_minutes' in data:
            event.reminder_minutes = data['reminder_minutes']
        if 'is_public' in data:
            event.is_public = data['is_public']
        if 'repeat' in data:
            event.repeat = data['repeat']
        
        event.save()
        
        # 참석자 업데이트
        if 'participants' in data:
            participant_ids = data['participants']
            participants = User.objects.filter(id__in=participant_ids)
            event.participants.set(participants)
        
        return JsonResponse({'success': True, 'message': '이벤트가 수정되었습니다.'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(["DELETE"])
def delete_calendar_event(request, event_id):
    """캘린더 이벤트 삭제 API"""
    try:
        event = get_object_or_404(CalendarEvent, id=event_id)
        
        # 권한 체크 (주최자만 삭제 가능)
        if event.organizer != request.user:
            return JsonResponse({'error': '삭제 권한이 없습니다.'}, status=403)
        
        event_title = event.title
        event.delete()
        
        # 활동 기록
        Activity.objects.create(
            user=request.user,
            activity_type='event_deleted',
            description=f"캘린더 이벤트 '{event_title}' 삭제"
        )
        
        return JsonResponse({'success': True, 'message': '이벤트가 삭제되었습니다.'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)