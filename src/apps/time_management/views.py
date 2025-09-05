"""
OneSquare Time Management - API Views

업무시간 관리 시스템의 REST API 엔드포인트
PWA 클라이언트와의 통신을 담당
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.db import transaction
from django.core.paginator import Paginator
from datetime import datetime, date, timedelta
import json
import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import WorkTimeRecord, WorkTimeSettings, WorkTimeSummary
from .services import (
    WorkTimeTrackingService, 
    WorkTimeStatisticsService, 
    ExcelExportService
)
from apps.auth_system.decorators import secure_api_view, admin_required

logger = logging.getLogger(__name__)


# PWA 메인 페이지 (HTML)
@login_required
def time_management_dashboard(request):
    """업무시간 관리 PWA 대시보드"""
    tracking_service = WorkTimeTrackingService()
    
    # 오늘의 근무 상태
    today_status = tracking_service.get_today_work_status(request.user)
    
    context = {
        'page_title': '업무시간 관리',
        'today_status': today_status,
        'user': request.user,
        'current_time': timezone.now(),
    }
    
    return render(request, 'time_management/dashboard.html', context)


# REST API 엔드포인트들

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_in(request):
    """출근 처리 API"""
    try:
        tracking_service = WorkTimeTrackingService()
        
        # GPS 위치 정보 (선택적)
        location_data = request.data.get('location', {})
        
        record = tracking_service.check_in_user(request.user, location_data)
        
        return Response({
            'success': True,
            'message': '출근 처리가 완료되었습니다.',
            'data': {
                'record_id': record.id,
                'check_in_time': record.check_in_time.isoformat(),
                'work_date': record.work_date.isoformat(),
                'status': record.get_status_display(),
            }
        }, status=status.HTTP_200_OK)
        
    except ValueError as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"출근 처리 API 오류: {request.user.username} - {str(e)}")
        return Response({
            'success': False,
            'message': '출근 처리 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_out(request):
    """퇴근 처리 API"""
    try:
        tracking_service = WorkTimeTrackingService()
        
        # GPS 위치 정보 (선택적)
        location_data = request.data.get('location', {})
        
        record = tracking_service.check_out_user(request.user, location_data)
        
        return Response({
            'success': True,
            'message': '퇴근 처리가 완료되었습니다.',
            'data': {
                'record_id': record.id,
                'check_out_time': record.check_out_time.isoformat(),
                'work_date': record.work_date.isoformat(),
                'total_work_hours': record.total_work_hours,
                'actual_work_hours': record.actual_work_hours,
                'overtime_hours': record.overtime_hours,
                'work_time_formatted': record.get_work_time_formatted(),
                'is_overtime': record.is_overtime,
                'status': record.get_status_display(),
            }
        }, status=status.HTTP_200_OK)
        
    except ValueError as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"퇴근 처리 API 오류: {request.user.username} - {str(e)}")
        return Response({
            'success': False,
            'message': '퇴근 처리 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def work_status(request):
    """현재 근무 상태 조회 API"""
    try:
        tracking_service = WorkTimeTrackingService()
        today_status = tracking_service.get_today_work_status(request.user)
        
        return Response({
            'success': True,
            'data': today_status
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"근무 상태 조회 API 오류: {request.user.username} - {str(e)}")
        return Response({
            'success': False,
            'message': '근무 상태 조회 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def daily_records(request):
    """일별 근무기록 조회 API"""
    try:
        # 쿼리 파라미터
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        page_num = int(request.GET.get('page', 1))
        page_size = min(int(request.GET.get('page_size', 20)), 100)  # 최대 100개
        
        # 기본값: 최근 30일
        if not start_date_str or not end_date_str:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=30)
        else:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # 기록 조회
        records_queryset = WorkTimeRecord.objects.filter(
            user=request.user,
            work_date__range=[start_date, end_date]
        ).order_by('-work_date')
        
        # 페이지네이션
        paginator = Paginator(records_queryset, page_size)
        page = paginator.get_page(page_num)
        
        # 데이터 직렬화
        records_data = []
        for record in page.object_list:
            records_data.append({
                'id': record.id,
                'work_date': record.work_date.isoformat(),
                'check_in_time': record.check_in_time.isoformat() if record.check_in_time else None,
                'check_out_time': record.check_out_time.isoformat() if record.check_out_time else None,
                'total_work_hours': record.total_work_hours,
                'actual_work_hours': record.actual_work_hours,
                'overtime_hours': record.overtime_hours,
                'work_time_formatted': record.get_work_time_formatted(),
                'is_overtime': record.is_overtime,
                'is_undertime': record.is_undertime,
                'status': record.get_status_display(),
                'record_type': record.get_record_type_display(),
                'memo': record.memo,
            })
        
        return Response({
            'success': True,
            'data': {
                'records': records_data,
                'pagination': {
                    'current_page': page.number,
                    'total_pages': paginator.num_pages,
                    'total_count': paginator.count,
                    'has_next': page.has_next(),
                    'has_previous': page.has_previous(),
                }
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"일별 근무기록 조회 API 오류: {request.user.username} - {str(e)}")
        return Response({
            'success': False,
            'message': '근무기록 조회 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monthly_statistics(request):
    """월간 통계 조회 API"""
    try:
        # 쿼리 파라미터
        year = int(request.GET.get('year', timezone.now().year))
        month = int(request.GET.get('month', timezone.now().month))
        
        stats_service = WorkTimeStatisticsService()
        monthly_stats = stats_service.calculate_monthly_summary(request.user, year, month)
        
        return Response({
            'success': True,
            'data': monthly_stats
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"월간 통계 조회 API 오류: {request.user.username} - {str(e)}")
        return Response({
            'success': False,
            'message': '월간 통계 조회 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def weekly_statistics(request):
    """주간 통계 조회 API"""
    try:
        # 쿼리 파라미터
        year = int(request.GET.get('year', timezone.now().year))
        week = int(request.GET.get('week', timezone.now().isocalendar()[1]))
        
        stats_service = WorkTimeStatisticsService()
        weekly_stats = stats_service.calculate_weekly_summary(request.user, year, week)
        
        return Response({
            'success': True,
            'data': weekly_stats
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"주간 통계 조회 API 오류: {request.user.username} - {str(e)}")
        return Response({
            'success': False,
            'message': '주간 통계 조회 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chart_data(request):
    """차트 데이터 조회 API"""
    try:
        # 쿼리 파라미터
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        
        # 기본값: 최근 14일
        if not start_date_str or not end_date_str:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=13)  # 14일
        else:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        stats_service = WorkTimeStatisticsService()
        chart_data = stats_service.generate_work_time_chart_data(
            request.user, start_date, end_date
        )
        
        return Response({
            'success': True,
            'data': chart_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"차트 데이터 조회 API 오류: {request.user.username} - {str(e)}")
        return Response({
            'success': False,
            'message': '차트 데이터 조회 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_memo(request, record_id):
    """근무기록 메모 업데이트 API"""
    try:
        memo = request.data.get('memo', '').strip()
        
        record = WorkTimeRecord.objects.get(
            id=record_id,
            user=request.user
        )
        
        record.memo = memo
        record.save(update_fields=['memo'])
        
        return Response({
            'success': True,
            'message': '메모가 업데이트되었습니다.',
            'data': {
                'record_id': record.id,
                'memo': record.memo
            }
        }, status=status.HTTP_200_OK)
        
    except WorkTimeRecord.DoesNotExist:
        return Response({
            'success': False,
            'message': '해당 근무기록을 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.error(f"메모 업데이트 API 오류: {request.user.username} - {str(e)}")
        return Response({
            'success': False,
            'message': '메모 업데이트 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 관리자 전용 API

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@admin_required
def adjust_work_time(request, record_id):
    """근무시간 수동 조정 API (관리자 전용)"""
    try:
        data = request.data
        check_in_time = datetime.fromisoformat(data['check_in_time'])
        check_out_time = datetime.fromisoformat(data['check_out_time'])
        reason = data.get('reason', '').strip()
        
        if not reason:
            return Response({
                'success': False,
                'message': '조정 사유를 입력해주세요.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        tracking_service = WorkTimeTrackingService()
        record = tracking_service.adjust_work_time(
            record_id, check_in_time, check_out_time, reason, request.user
        )
        
        return Response({
            'success': True,
            'message': '근무시간이 조정되었습니다.',
            'data': {
                'record_id': record.id,
                'check_in_time': record.check_in_time.isoformat(),
                'check_out_time': record.check_out_time.isoformat(),
                'total_work_hours': record.total_work_hours,
                'actual_work_hours': record.actual_work_hours,
                'overtime_hours': record.overtime_hours,
                'adjustment_reason': record.adjustment_reason,
                'adjusted_by': record.approved_by.username if record.approved_by else None,
            }
        }, status=status.HTTP_200_OK)
        
    except ValueError as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"근무시간 조정 API 오류: {request.user.username} - {str(e)}")
        return Response({
            'success': False,
            'message': '근무시간 조정 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_to_notion(request, record_id):
    """Notion 동기화 API"""
    try:
        record = WorkTimeRecord.objects.get(
            id=record_id,
            user=request.user
        )
        
        tracking_service = WorkTimeTrackingService()
        success = tracking_service.sync_to_notion(record)
        
        if success:
            return Response({
                'success': True,
                'message': 'Notion 동기화가 완료되었습니다.',
                'data': {
                    'record_id': record.id,
                    'notion_page_id': record.notion_page_id,
                    'last_synced': record.notion_last_synced.isoformat() if record.notion_last_synced else None,
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': 'Notion 동기화에 실패했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except WorkTimeRecord.DoesNotExist:
        return Response({
            'success': False,
            'message': '해당 근무기록을 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Exception as e:
        logger.error(f"Notion 동기화 API 오류: {request.user.username} - {str(e)}")
        return Response({
            'success': False,
            'message': 'Notion 동기화 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 엑셀 내보내기

@login_required
@require_http_methods(["GET"])
def export_monthly_excel(request):
    """월간 근무시간 엑셀 내보내기"""
    try:
        year = int(request.GET.get('year', timezone.now().year))
        month = int(request.GET.get('month', timezone.now().month))
        
        export_service = ExcelExportService()
        excel_data = export_service.export_monthly_report(request.user, year, month)
        
        filename = f"근무시간_{request.user.username}_{year}년{month:02d}월.xlsx"
        
        response = HttpResponse(
            excel_data,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        logger.error(f"엑셀 내보내기 오류: {request.user.username} - {str(e)}")
        return JsonResponse({
            'success': False,
            'message': '엑셀 내보내기 중 오류가 발생했습니다.'
        }, status=500)


# 통계 캐시 업데이트 (백그라운드 작업용)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@admin_required
def update_statistics_cache(request):
    """통계 캐시 업데이트 API (관리자 전용)"""
    try:
        data = request.data
        user_id = data.get('user_id')
        summary_type = data.get('summary_type', 'monthly')
        year = int(data.get('year', timezone.now().year))
        month = data.get('month')
        week = data.get('week')
        
        if user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=user_id)
        else:
            user = request.user
        
        stats_service = WorkTimeStatisticsService()
        stats_service.update_summary_cache(
            user, summary_type, year, 
            month=int(month) if month else None,
            week=int(week) if week else None
        )
        
        return Response({
            'success': True,
            'message': '통계 캐시가 업데이트되었습니다.'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"통계 캐시 업데이트 오류: {request.user.username} - {str(e)}")
        return Response({
            'success': False,
            'message': '통계 캐시 업데이트 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
