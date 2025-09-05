"""
OneSquare 매출 관리 - 알림 시스템 API 뷰
실시간 알림 조회 및 대시보드 통합 API
"""

import logging
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json

from .alerts import RevenueAlertManager, send_revenue_notification
from .permissions import RevenuePermissionManager, UserRole, require_revenue_permission
from .models import RevenueAlert

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_alerts(request):
    """사용자별 맞춤 알림 조회"""
    try:
        alert_manager = RevenueAlertManager()
        user_alerts = alert_manager.get_user_specific_alerts(request.user)
        
        return Response({
            'success': True,
            'data': user_alerts,
            'user': {
                'username': request.user.username,
                'full_name': request.user.get_full_name(),
                'role': user_alerts['user_role']
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"사용자 알림 조회 실패 ({request.user.username}): {e}")
        return Response({
            'success': False,
            'error': '알림 조회 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_widgets(request):
    """대시보드용 위젯 데이터"""
    try:
        alert_manager = RevenueAlertManager()
        widget_data = alert_manager.get_dashboard_widgets(request.user)
        
        return Response({
            'success': True,
            'widgets': widget_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"대시보드 위젯 조회 실패: {e}")
        return Response({
            'success': False,
            'error': '위젯 데이터 조회 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_alert_summary(request):
    """알림 요약 정보 (헤더 알림 뱃지용)"""
    try:
        alert_manager = RevenueAlertManager()
        user_alerts = alert_manager.get_user_specific_alerts(request.user)
        
        # 읽지 않은 알림 개수 계산
        unread_count = 0
        high_priority_count = 0
        
        for alert_type, alert_list in user_alerts['alerts'].items():
            for alert in alert_list:
                unread_count += 1
                if alert.get('severity') == 'high':
                    high_priority_count += 1
        
        # 저장된 알림 중 읽지 않은 것들도 포함
        saved_unread = RevenueAlert.objects.filter(
            is_read=False,
            created_at__gte=request.user.date_joined  # 사용자 가입 이후 알림만
        ).count()
        
        return Response({
            'unread_count': unread_count + saved_unread,
            'high_priority_count': high_priority_count,
            'last_updated': user_alerts['summary']['generated_at']
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"알림 요약 조회 실패: {e}")
        return Response({
            'unread_count': 0,
            'high_priority_count': 0,
            'error': str(e)
        }, status=status.HTTP_200_OK)  # 알림은 실패해도 500 에러 내지 않음

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_alert_read(request, alert_id):
    """알림 읽음 처리"""
    try:
        alert_manager = RevenueAlertManager()
        success = alert_manager.mark_alert_as_read(alert_id, request.user)
        
        if success:
            return Response({
                'success': True,
                'message': '알림이 읽음 처리되었습니다.'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': '알림을 찾을 수 없습니다.'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        logger.error(f"알림 읽음 처리 실패: {e}")
        return Response({
            'success': False,
            'error': '알림 처리 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_revenue_permission('write')
def create_custom_alert(request):
    """커스텀 알림 생성 (관리자만)"""
    user_role = RevenuePermissionManager.get_user_role(request.user)
    
    if user_role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        return Response({
            'success': False,
            'error': '알림 생성 권한이 없습니다.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        alert_type = request.data.get('alert_type', 'custom')
        message = request.data.get('message', '')
        severity = request.data.get('severity', 'medium')
        metadata = request.data.get('metadata', {})
        
        if not message:
            return Response({
                'success': False,
                'error': '알림 메시지가 필요합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        alert_manager = RevenueAlertManager()
        success = alert_manager.create_system_alert(
            alert_type=alert_type,
            message=message,
            severity=severity,
            metadata=metadata
        )
        
        if success:
            return Response({
                'success': True,
                'message': '알림이 생성되었습니다.'
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'success': False,
                'error': '알림 생성에 실패했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"커스텀 알림 생성 실패: {e}")
        return Response({
            'success': False,
            'error': '알림 생성 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_alert_history(request):
    """알림 히스토리 조회"""
    try:
        page = int(request.GET.get('page', 1))
        per_page = int(request.GET.get('per_page', 20))
        alert_type = request.GET.get('type', '')
        severity = request.GET.get('severity', '')
        
        # 기본 쿼리셋
        queryset = RevenueAlert.objects.all().order_by('-created_at')
        
        # 필터링
        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)
        if severity:
            queryset = queryset.filter(severity=severity)
        
        # 권한에 따른 필터링 (관리자가 아니면 제한)
        user_role = RevenuePermissionManager.get_user_role(request.user)
        if user_role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
            # 일반 사용자는 최근 30일 히스토리만 조회 가능
            from django.utils import timezone
            from datetime import timedelta
            thirty_days_ago = timezone.now() - timedelta(days=30)
            queryset = queryset.filter(created_at__gte=thirty_days_ago)
        
        # 페이지네이션
        total_count = queryset.count()
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        alerts = queryset[start_idx:end_idx]
        
        # 데이터 직렬화
        alert_data = []
        for alert in alerts:
            alert_data.append({
                'id': str(alert.id),
                'alert_type': alert.alert_type,
                'severity': alert.severity,
                'message': alert.message,
                'metadata': alert.metadata,
                'is_read': alert.is_read,
                'created_at': alert.created_at.isoformat(),
                'read_at': alert.read_at.isoformat() if alert.read_at else None,
                'read_by': alert.read_by.username if alert.read_by else None
            })
        
        return Response({
            'success': True,
            'alerts': alert_data,
            'pagination': {
                'current_page': page,
                'per_page': per_page,
                'total_count': total_count,
                'total_pages': (total_count + per_page - 1) // per_page
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"알림 히스토리 조회 실패: {e}")
        return Response({
            'success': False,
            'error': '히스토리 조회 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_alert_statistics(request):
    """알림 통계 데이터 (관리자용)"""
    user_role = RevenuePermissionManager.get_user_role(request.user)
    
    if user_role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        return Response({
            'success': False,
            'error': '통계 조회 권한이 없습니다.'
        }, status=status.HTTP_403_FORBIDDEN)
    
    try:
        from django.db.models import Count
        from django.utils import timezone
        from datetime import timedelta
        
        # 최근 30일 통계
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        # 알림 유형별 통계
        type_stats = RevenueAlert.objects.filter(
            created_at__gte=thirty_days_ago
        ).values('alert_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # 심각도별 통계
        severity_stats = RevenueAlert.objects.filter(
            created_at__gte=thirty_days_ago
        ).values('severity').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # 일별 알림 발생 추이
        daily_stats = []
        for i in range(7):  # 최근 7일
            date = timezone.now().date() - timedelta(days=i)
            daily_count = RevenueAlert.objects.filter(
                created_at__date=date
            ).count()
            daily_stats.append({
                'date': date.isoformat(),
                'count': daily_count
            })
        
        daily_stats.reverse()  # 시간순 정렬
        
        # 읽지 않은 알림 통계
        unread_count = RevenueAlert.objects.filter(is_read=False).count()
        total_count = RevenueAlert.objects.count()
        read_rate = (total_count - unread_count) / total_count * 100 if total_count > 0 else 0
        
        return Response({
            'success': True,
            'statistics': {
                'type_distribution': list(type_stats),
                'severity_distribution': list(severity_stats),
                'daily_trend': daily_stats,
                'read_statistics': {
                    'total_alerts': total_count,
                    'unread_alerts': unread_count,
                    'read_rate': round(read_rate, 1)
                }
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"알림 통계 조회 실패: {e}")
        return Response({
            'success': False,
            'error': '통계 조회 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_alert_refresh(request):
    """알림 새로고침 트리거 (실시간 업데이트)"""
    try:
        alert_manager = RevenueAlertManager()
        user_alerts = alert_manager.get_user_specific_alerts(request.user)
        
        # WebSocket이나 Server-Sent Events를 통한 실시간 푸시
        # 여기서는 HTTP 응답으로 최신 알림 반환
        
        return Response({
            'success': True,
            'alerts': user_alerts,
            'refreshed_at': user_alerts['summary']['generated_at']
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"알림 새로고침 실패: {e}")
        return Response({
            'success': False,
            'error': '알림 새로고침 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# PWA 푸시 알림 구독 관리
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def subscribe_push_notifications(request):
    """PWA 푸시 알림 구독"""
    try:
        subscription_data = request.data.get('subscription')
        
        if not subscription_data:
            return Response({
                'success': False,
                'error': '구독 데이터가 필요합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 푸시 구독 정보를 데이터베이스에 저장
        # 실제 구현에서는 별도 PushSubscription 모델 사용
        
        logger.info(f"사용자 {request.user.username} 푸시 알림 구독")
        
        return Response({
            'success': True,
            'message': '푸시 알림 구독이 완료되었습니다.'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"푸시 알림 구독 실패: {e}")
        return Response({
            'success': False,
            'error': '구독 처리 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@require_http_methods(["POST"])
def webhook_alert_trigger(request):
    """외부 시스템에서 알림 트리거 (웹훅)"""
    try:
        # API 키 인증 (실제 구현에서는 적절한 인증 추가)
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != getattr(settings, 'WEBHOOK_API_KEY', ''):
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        
        webhook_data = json.loads(request.body)
        alert_type = webhook_data.get('type', 'external')
        message = webhook_data.get('message', '')
        severity = webhook_data.get('severity', 'medium')
        metadata = webhook_data.get('metadata', {})
        
        if not message:
            return JsonResponse({'error': 'Message required'}, status=400)
        
        # 시스템 알림 생성
        alert_manager = RevenueAlertManager()
        success = alert_manager.create_system_alert(
            alert_type=alert_type,
            message=message,
            severity=severity,
            metadata=metadata
        )
        
        if success:
            # 관련 사용자들에게 알림 전송
            from django.contrib.auth.models import User
            admin_users = User.objects.filter(
                groups__name__in=['super_admin', 'admin']
            )
            
            for admin in admin_users:
                send_revenue_notification(admin, {
                    'type': alert_type,
                    'message': message,
                    'severity': severity
                })
        
        return JsonResponse({
            'success': success,
            'message': 'Alert processed successfully' if success else 'Alert processing failed'
        }, status=200 if success else 500)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"웹훅 알림 처리 실패: {e}")
        return JsonResponse({'error': 'Webhook processing failed'}, status=500)