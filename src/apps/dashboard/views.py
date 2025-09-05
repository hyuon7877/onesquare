"""
OneSquare 통합 관리 대시보드 시스템 - Views
실시간 데이터 시각화 및 권한별 접근 제어
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
import json

from apps.auth_system.decorators import permission_required
from apps.auth_system.models import CustomUser
from apps.revenue.models import RevenueRecord, Project, Client, RevenueTarget
from apps.calendar_system.models import CalendarEvent
from .models import (
    DashboardWidget, UserDashboard, UserWidgetSettings,
    DashboardNotification, NotificationReadStatus,
    DashboardDataCache, SystemHealthMetric
)
from .services import DashboardDataService, NotificationService
from .layout_manager import get_layout_manager
from .notion_notification_service import NotionNotificationService


@login_required
@permission_required(['can_view_dashboard'])
def dashboard_main(request):
    """메인 대시보드 페이지"""
    
    # 레이아웃 매니저를 통한 대시보드 설정
    layout_manager = get_layout_manager(request.user)
    user_dashboard = layout_manager.setup_user_dashboard()
    
    # 레이아웃 매니저를 통한 위젯 조회
    available_widgets = layout_manager.get_available_widgets()
    user_widgets = layout_manager.get_user_widgets()
    
    # 읽지 않은 알림 수
    unread_notifications_count = _get_unread_notifications_count(request.user)
    
    context = {
        'user_dashboard': user_dashboard,
        'user_widgets': user_widgets,
        'available_widgets': available_widgets,
        'unread_notifications_count': unread_notifications_count,
        'user_type': request.user.user_type,
    }
    
    return render(request, 'dashboard/main.html', context)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_data_api(request):
    """대시보드 데이터 API - 실시간 데이터 제공"""
    
    data_service = DashboardDataService()
    widget_type = request.GET.get('widget_type')
    data_source = request.GET.get('data_source')
    time_range = request.GET.get('time_range', '7d')
    
    try:
        if widget_type and data_source:
            data = data_service.get_widget_data(
                widget_type=widget_type,
                data_source=data_source,
                user=request.user,
                time_range=time_range
            )
            return Response(data)
        else:
            # 전체 대시보드 데이터
            dashboard_data = data_service.get_dashboard_overview(request.user)
            return Response(dashboard_data)
            
    except Exception as e:
        return Response({
            'error': str(e),
            'message': '데이터를 불러오는 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def revenue_dashboard_api(request):
    """매출 대시보드 데이터 API"""
    
    # 권한 체크
    if request.user.user_type not in ['SUPER_ADMIN', 'MANAGER']:
        return Response({
            'error': '접근 권한이 없습니다.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        data_service = DashboardDataService()
        revenue_data = data_service.get_revenue_dashboard_data(request.user)
        return Response(revenue_data)
        
    except Exception as e:
        return Response({
            'error': str(e),
            'message': '매출 데이터를 불러오는 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calendar_dashboard_api(request):
    """캘린더 대시보드 데이터 API"""
    
    try:
        # 다가오는 이벤트 (7일)
        start_date = timezone.now()
        end_date = start_date + timedelta(days=7)
        
        events = CalendarEvent.objects.filter(
            Q(creator=request.user) | Q(attendees=request.user),
            start_datetime__range=[start_date, end_date],
            is_active=True
        ).distinct().select_related('creator', 'category')[:10]
        
        events_data = []
        for event in events:
            if event.can_view(request.user):
                events_data.append({
                    'id': event.id,
                    'title': event.title,
                    'start': event.start_datetime.isoformat(),
                    'end': event.end_datetime.isoformat(),
                    'type': event.event_type,
                    'priority': event.priority,
                    'location': event.location,
                    'category': event.category.name if event.category else '',
                    'category_color': event.category.color if event.category else '#3788d8',
                })
        
        # 오늘의 이벤트
        today = timezone.now().date()
        today_events = CalendarEvent.objects.filter(
            Q(creator=request.user) | Q(attendees=request.user),
            start_datetime__date=today,
            is_active=True
        ).distinct().count()
        
        return Response({
            'upcoming_events': events_data,
            'today_events_count': today_events,
            'total_events_this_week': len(events_data)
        })
        
    except Exception as e:
        return Response({
            'error': str(e),
            'message': '캘린더 데이터를 불러오는 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def system_health_api(request):
    """시스템 상태 API"""
    
    # 관리자만 접근 가능
    if request.user.user_type != 'SUPER_ADMIN':
        return Response({
            'error': '접근 권한이 없습니다.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        # 최근 시스템 메트릭 조회
        metrics = {}
        for metric_type, _ in SystemHealthMetric.METRIC_TYPE_CHOICES:
            latest_metric = SystemHealthMetric.objects.filter(
                metric_type=metric_type
            ).order_by('-recorded_at').first()
            
            if latest_metric:
                metrics[metric_type] = {
                    'value': latest_metric.value,
                    'unit': latest_metric.unit,
                    'status': latest_metric.status,
                    'recorded_at': latest_metric.recorded_at.isoformat(),
                }
        
        # 전체 시스템 상태 계산
        critical_count = sum(1 for m in metrics.values() if m.get('status') == 'critical')
        warning_count = sum(1 for m in metrics.values() if m.get('status') == 'warning')
        
        overall_status = 'normal'
        if critical_count > 0:
            overall_status = 'critical'
        elif warning_count > 0:
            overall_status = 'warning'
        
        return Response({
            'metrics': metrics,
            'overall_status': overall_status,
            'critical_count': critical_count,
            'warning_count': warning_count,
        })
        
    except Exception as e:
        return Response({
            'error': str(e),
            'message': '시스템 상태를 불러오는 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def save_widget_layout(request):
    """위젯 레이아웃 저장 (드래그 앤 드롭용)"""
    
    try:
        data = json.loads(request.body)
        layout_manager = get_layout_manager(request.user)
        
        success, message = layout_manager.update_widget_layout(data.get('widgets', []))
        
        return JsonResponse({
            'success': success,
            'message': message
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'레이아웃 저장 중 오류가 발생했습니다: {str(e)}'
        }, status=500)


@login_required
def add_widget(request):
    """위젯 추가"""
    
    if request.method == 'POST':
        try:
            widget_id = request.POST.get('widget_id')
            
            # 레이아웃 매니저를 통한 위젯 추가
            layout_manager = get_layout_manager(request.user)
            success, message = layout_manager.add_widget_to_dashboard(widget_id)
            
            return JsonResponse({
                'success': success,
                'message': message
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'위젯 추가 중 오류가 발생했습니다: {str(e)}'
            })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications_api(request):
    """알림 API"""
    
    try:
        notion_service = NotionNotificationService()
        
        # Notion 기반 알림 데이터 조회
        notifications_data = notion_service.get_user_notifications(
            user=request.user,
            limit=int(request.GET.get('limit', 20))
        )
        
        # 알림 통계 조회
        stats = notion_service.get_notification_stats(request.user)
        
        return Response({
            'success': True,
            'notifications': notifications_data,
            'stats': stats,
            'unread_count': stats.get('unread', 0)
        })
        
    except Exception as e:
        return Response({
            'error': str(e),
            'message': '알림을 불러오는 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def mark_notification_read(request, notification_id):
    """알림 읽음 처리"""
    
    try:
        notion_service = NotionNotificationService()
        
        # Notion 알림 서비스를 통한 읽음 처리
        success = notion_service.mark_notification_read(request.user, notification_id)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': '알림이 읽음 처리되었습니다.'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': '알림을 찾을 수 없습니다.'
            }, status=404)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'알림 처리 중 오류가 발생했습니다: {str(e)}'
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_notion_sync(request):
    """Notion 변경사항 수동 동기화 트리거"""
    try:
        from .notion_notification_service import NotionChangePoller
        
        poller = NotionChangePoller()
        poller.run_polling_cycle()
        
        return Response({
            'success': True,
            'message': 'Notion 동기화가 완료되었습니다.'
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e),
            'message': 'Notion 동기화 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@login_required
def remove_widget(request, widget_id):
    """위젯 제거"""
    
    if request.method == 'POST':
        try:
            layout_manager = get_layout_manager(request.user)
            success, message = layout_manager.remove_widget_from_dashboard(widget_id)
            
            return JsonResponse({
                'success': success,
                'message': message
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'위젯 제거 중 오류가 발생했습니다: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'POST 요청만 허용됩니다.'})


@login_required
def reset_dashboard_layout(request):
    """대시보드 레이아웃 초기화"""
    
    if request.method == 'POST':
        try:
            layout_manager = get_layout_manager(request.user)
            layout_manager.reset_to_default_layout()
            
            return JsonResponse({
                'success': True,
                'message': '대시보드가 기본 레이아웃으로 초기화되었습니다.'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'레이아웃 초기화 중 오류가 발생했습니다: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'POST 요청만 허용됩니다.'})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def dashboard_layout_api(request):
    """대시보드 레이아웃 API"""
    
    layout_manager = get_layout_manager(request.user)
    
    if request.method == 'GET':
        # 현재 레이아웃 내보내기
        layout_data = layout_manager.export_layout()
        return Response(layout_data)
    
    elif request.method == 'POST':
        try:
            action = request.data.get('action')
            
            if action == 'update_layout':
                # 레이아웃 업데이트
                layouts = request.data.get('layouts', [])
                success, message = layout_manager.update_widget_layout(layouts)
                
                return Response({
                    'success': success,
                    'message': message
                })
                
            elif action == 'import_layout':
                # 레이아웃 가져오기
                layout_data = request.data.get('layout_data')
                success, message = layout_manager.import_layout(layout_data)
                
                return Response({
                    'success': success,
                    'message': message
                })
                
            else:
                return Response({
                    'success': False,
                    'message': '잘못된 액션입니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response({
                'success': False,
                'message': f'레이아웃 처리 중 오류가 발생했습니다: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_dashboard_info_api(request):
    """사용자 대시보드 정보 API"""
    
    try:
        layout_manager = get_layout_manager(request.user)
        user_dashboard = UserDashboard.objects.filter(user=request.user).first()
        
        if not user_dashboard:
            user_dashboard = layout_manager.setup_user_dashboard()
        
        # 사용 가능한 위젯 수
        available_count = layout_manager.get_available_widgets().count()
        
        # 현재 사용 중인 위젯 수
        active_count = layout_manager.get_user_widgets().count()
        
        return Response({
            'user_type': request.user.user_type,
            'user_type_display': request.user.get_user_type_display(),
            'layout_type': user_dashboard.layout_type,
            'theme': user_dashboard.theme,
            'primary_color': user_dashboard.primary_color,
            'widget_stats': {
                'available': available_count,
                'active': active_count,
                'completion_rate': (active_count / available_count * 100) if available_count > 0 else 0
            },
            'last_updated': user_dashboard.updated_at.isoformat()
        })
        
    except Exception as e:
        return Response({
            'error': str(e),
            'message': '대시보드 정보를 불러오는 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def _get_unread_notifications_count(user):
    """읽지 않은 알림 수 조회"""
    
    # 사용자 대상 전체 알림
    all_notifications = DashboardNotification.objects.filter(
        Q(target_users=user) | Q(target_user_types__contains=[user.user_type]),
        is_active=True
    )
    
    # 읽음 처리된 알림 ID들
    read_notification_ids = NotificationReadStatus.objects.filter(
        user=user,
        is_read=True
    ).values_list('notification_id', flat=True)
    
    # 읽지 않은 알림 수
    unread_count = all_notifications.exclude(
        id__in=read_notification_ids
    ).count()
    
    return unread_count


@api_view(['GET'])
def dashboard_status(request):
    """Dashboard system status check"""
    return Response({
        'message': 'Dashboard system is ready',
        'status': 'success',
        'features': {
            'real_time_data': True,
            'svg_charts': True,
            'role_based_access': True,
            'notification_system': True,
            'pwa_support': True,
            'offline_support': True,
        }
    })


@login_required
def notification_settings_view(request):
    """알림 설정 페이지"""
    context = {
        'title': '알림 설정 - OneSquare',
        'page_title': '알림 설정',
        'description': 'PWA 푸시 알림 및 시스템 알림을 관리합니다'
    }
    
    return render(request, 'dashboard/notification_settings.html', context)