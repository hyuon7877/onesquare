from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.db.models import Count, Q, Sum
from field_reports.models import FieldReport
# collaboration 모델 사용 (dashboard 모델 대신)
from collaboration.models import Activity, Notification
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
    reports_month = FieldReport.objects.filter(created_at__gte=month_ago).count()
    
    # 최근 리포트
    recent_reports = FieldReport.objects.select_related('author').order_by('-created_at')[:5]
    
    # 일별 리포트 생성 추이 (최근 7일)
    daily_reports = []
    for i in range(7):
        date = today - timedelta(days=i)
        count = FieldReport.objects.filter(
            created_at__date=date
        ).count()
        daily_reports.append({
            'date': date.strftime('%m/%d'),
            'count': count
        })
    daily_reports.reverse()
    
    # 리포트 타입별 통계
    report_types_stats = FieldReport.objects.values('report_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # 작업 현황 통계 (상태별)
    status_distribution = {
        'draft': 0,
        'submitted': 0,
        'approved': 0,
        'rejected': 0
    }
    for item in reports_by_status:
        if item['status'] in status_distribution:
            status_distribution[item['status']] = item['count']
    
    context = {
        'user': request.user,
        'current_time': now,
        # 사용자 통계
        'total_users': total_users,
        'new_users_week': new_users_week,
        'new_users_month': new_users_month,
        # 리포트 통계
        'total_reports': total_reports,
        'reports_week': reports_week,
        'reports_month': reports_month,
        'recent_reports': recent_reports,
        'daily_reports': daily_reports,
        'report_types_stats': report_types_stats,
        'status_distribution': status_distribution,
        # 성장률 계산
        'growth_rate': round((reports_week / reports_month * 100) if reports_month > 0 else 0, 1),
    }
    return render(request, 'dashboard/dashboard.html', context)

@login_required
@require_http_methods(["GET"])
def get_statistics(request):
    """대시보드 통계 데이터 API"""
    
    # 샘플 통계 데이터 (실제로는 DB에서 가져와야 함)
    stats = {
        'total_users': 1234,
        'active_projects': 42,
        'completed_tasks': 567,
        'pending_reports': 23,
        'growth_rate': 12.5,
        'user_growth': [
            {'month': '1월', 'value': 980},
            {'month': '2월', 'value': 1050},
            {'month': '3월', 'value': 1120},
            {'month': '4월', 'value': 1180},
            {'month': '5월', 'value': 1234},
        ]
    }
    
    return JsonResponse(stats)

@login_required
@require_http_methods(["GET"])
def get_recent_activities(request):
    """최근 활동 데이터 API"""
    
    # 샘플 활동 데이터
    activities = [
        {
            'id': 1,
            'type': 'task_completed',
            'user': '김철수',
            'description': '프로젝트 A 작업 완료',
            'timestamp': (timezone.now() - timedelta(minutes=5)).isoformat(),
            'icon': 'check-circle'
        },
        {
            'id': 2,
            'type': 'report_submitted',
            'user': '이영희',
            'description': '월간 보고서 제출',
            'timestamp': (timezone.now() - timedelta(minutes=15)).isoformat(),
            'icon': 'document'
        },
        {
            'id': 3,
            'type': 'user_joined',
            'user': '박민수',
            'description': '새 팀원 합류',
            'timestamp': (timezone.now() - timedelta(hours=1)).isoformat(),
            'icon': 'user-plus'
        },
        {
            'id': 4,
            'type': 'milestone_reached',
            'user': '시스템',
            'description': '목표 달성: 1000 사용자',
            'timestamp': (timezone.now() - timedelta(hours=2)).isoformat(),
            'icon': 'trophy'
        },
    ]
    
    return JsonResponse({'activities': activities})

@login_required
@require_http_methods(["GET"])
def get_notifications(request):
    """알림 데이터 API"""
    
    notifications = [
        {
            'id': 1,
            'type': 'info',
            'title': '시스템 업데이트',
            'message': '새로운 기능이 추가되었습니다.',
            'unread': True,
            'timestamp': timezone.now().isoformat()
        },
        {
            'id': 2,
            'type': 'warning',
            'title': '작업 마감 임박',
            'message': '프로젝트 B가 내일 마감입니다.',
            'unread': True,
            'timestamp': (timezone.now() - timedelta(hours=1)).isoformat()
        },
        {
            'id': 3,
            'type': 'success',
            'title': '목표 달성',
            'message': '이번 달 목표를 달성했습니다!',
            'unread': False,
            'timestamp': (timezone.now() - timedelta(days=1)).isoformat()
        },
    ]
    
    unread_count = sum(1 for n in notifications if n['unread'])
    
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
                    'label': '완료된 작업',
                    'data': [12, 19, 15, 25, 22],
                    'borderColor': '#0A84FF',
                    'tension': 0.3
                },
                {
                    'label': '새 작업',
                    'data': [8, 15, 12, 18, 20],
                    'borderColor': '#5856D6',
                    'tension': 0.3
                }
            ]
        }
    elif chart_type == 'pie':
        # 파이 차트 데이터
        data = {
            'labels': ['완료', '진행중', '대기', '보류'],
            'datasets': [{
                'data': [45, 30, 15, 10],
                'backgroundColor': ['#34C759', '#0A84FF', '#FFD60A', '#FF3B30']
            }]
        }
    elif chart_type == 'bar':
        # 바 차트 데이터
        data = {
            'labels': ['월', '화', '수', '목', '금'],
            'datasets': [{
                'label': '일일 활동',
                'data': [65, 78, 90, 81, 95],
                'backgroundColor': '#0A84FF'
            }]
        }
    else:
        data = {}
    
    return JsonResponse(data)

@login_required
@require_http_methods(["POST"])
def mark_notification_read(request):
    """알림 읽음 처리 API"""
    try:
        data = json.loads(request.body)
        notification_id = data.get('id')
        
        # 실제로는 DB에서 알림 상태를 업데이트해야 함
        # notification = Notification.objects.get(id=notification_id, user=request.user)
        # notification.is_read = True
        # notification.save()
        
        return JsonResponse({'success': True, 'message': '알림이 읽음 처리되었습니다.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@login_required
def calendar_view(request):
    """캘린더/일정 관리 페이지"""
    from datetime import datetime, timedelta
    from django.contrib.auth.models import User
    
    # 예시 일정 데이터
    today = datetime.now()
    events = []
    
    # 이번 주 일정 생성
    for i in range(7):
        date = today + timedelta(days=i)
        if i % 2 == 0:
            events.append({
                'date': date.strftime('%Y-%m-%d'),
                'title': f'프로젝트 미팅 {i+1}',
                'time': '14:00',
                'type': 'meeting',
                'participants': ['김철수', '이영희', '박민수']
            })
    
    context = {
        'events': events,
        'current_month': today.strftime('%Y년 %m월'),
        'today': today.strftime('%Y-%m-%d'),
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
