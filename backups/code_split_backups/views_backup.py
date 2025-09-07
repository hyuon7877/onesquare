"""
OneSquare 매출 관리 시스템 - Views
권한별 매출 데이터 접근 제어 및 API 엔드포인트
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Sum, Q, Count, Avg
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from decimal import Decimal
from datetime import datetime, date, timedelta
import json
import logging

from .models import (
    RevenueRecord, RevenueCategory, Client, Project, 
    RevenueTarget, RevenueAlert, RevenueReport
)
from .permissions import (
    RevenuePermission, RevenueReadOnlyPermission, 
    RevenuePermissionManager, UserRole,
    require_revenue_permission, get_user_revenue_permissions
)

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([RevenueReadOnlyPermission])
def revenue_dashboard_data(request):
    """매출 대시보드 데이터"""
    user_role = RevenuePermissionManager.get_user_role(request.user)
    
    # 사용자 권한에 따른 쿼리셋
    queryset = RevenuePermissionManager.filter_revenue_queryset(
        RevenueRecord.objects.all(), request.user
    )
    
    # 오늘 날짜 기준 통계
    today = date.today()
    this_month_start = today.replace(day=1)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
    
    # 이번 달 매출
    this_month_revenue = queryset.filter(
        revenue_date__gte=this_month_start,
        is_confirmed=True
    ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0')
    
    # 지난 달 매출
    last_month_revenue = queryset.filter(
        revenue_date__gte=last_month_start,
        revenue_date__lt=this_month_start,
        is_confirmed=True
    ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0')
    
    # 증감률 계산
    growth_rate = 0
    if last_month_revenue > 0:
        growth_rate = float((this_month_revenue - last_month_revenue) / last_month_revenue * 100)
    
    # 미수금
    pending_revenue = queryset.filter(
        payment_status='pending'
    ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0')
    
    # 연체 매출
    overdue_revenue = queryset.filter(
        payment_status='overdue'
    ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0')
    
    # 최근 매출 기록 (최대 5개)
    recent_revenues = queryset.order_by('-created_at')[:5]
    recent_data = []
    
    for revenue in recent_revenues:
        serializer_data = {
            'id': str(revenue.id),
            'project_name': revenue.project.name,
            'client_name': revenue.client.name,
            'amount': float(revenue.net_amount),
            'revenue_date': revenue.revenue_date.isoformat(),
            'payment_status': revenue.payment_status
        }
        
        # 마스킹 적용
        masked_data = RevenuePermissionManager.mask_revenue_data(
            serializer_data, request.user
        )
        recent_data.append(masked_data)
    
    dashboard_data = {
        'this_month_revenue': float(this_month_revenue),
        'last_month_revenue': float(last_month_revenue),
        'growth_rate': growth_rate,
        'pending_revenue': float(pending_revenue),
        'overdue_revenue': float(overdue_revenue),
        'recent_revenues': recent_data,
        'user_permissions': get_user_revenue_permissions(request.user)
    }
    
    # 전체 데이터 마스킹 (필요한 경우)
    if user_role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        dashboard_data = RevenuePermissionManager.mask_revenue_data(
            dashboard_data, request.user
        )
    
    return Response(dashboard_data)

@login_required
@require_revenue_permission('read')
def revenue_dashboard_view(request):
    """매출 대시보드 페이지"""
    user_permissions = get_user_revenue_permissions(request.user)
    
    context = {
        'user_permissions': user_permissions,
        'page_title': '매출 관리 대시보드'
    }
    
    return render(request, 'revenue/dashboard.html', context)

@login_required
@require_revenue_permission('read') 
def revenue_list_view(request):
    """매출 목록 페이지"""
    # 필터 옵션들
    categories = RevenueCategory.objects.filter(is_active=True)
    clients = Client.objects.filter(is_active=True)
    
    # 사용자 권한에 따라 클라이언트 목록 필터링
    user_role = RevenuePermissionManager.get_user_role(request.user)
    if user_role == UserRole.CLIENT:
        user_client = getattr(request.user, 'client_profile', None)
        if user_client:
            clients = clients.filter(id=user_client.id)
        else:
            clients = Client.objects.none()
    
    context = {
        'categories': categories,
        'clients': clients,
        'payment_statuses': RevenueRecord.PAYMENT_STATUS_CHOICES,
        'user_permissions': get_user_revenue_permissions(request.user)
    }
    
    return render(request, 'revenue/list.html', context)

@api_view(['GET'])
@permission_classes([RevenueReadOnlyPermission])
def revenue_list_api(request):
    """매출 목록 API"""
    # 사용자 권한에 따른 쿼리셋
    queryset = RevenuePermissionManager.filter_revenue_queryset(
        RevenueRecord.objects.select_related('project', 'client', 'category'), 
        request.user
    )
    
    # 필터링 적용
    queryset = apply_revenue_filters(queryset, request)
    
    # 페이지네이션
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 20))
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(page)
    
    # 데이터 직렬화
    revenue_data = []
    for revenue in page_obj:
        item_data = {
            'id': str(revenue.id),
            'project_name': revenue.project.name,
            'project_code': revenue.project.code,
            'client_name': revenue.client.name,
            'category_name': revenue.category.name,
            'revenue_type': revenue.get_revenue_type_display(),
            'amount': float(revenue.amount),
            'net_amount': float(revenue.net_amount),
            'revenue_date': revenue.revenue_date.isoformat(),
            'payment_status': revenue.get_payment_status_display(),
            'is_confirmed': revenue.is_confirmed,
            'sales_person': revenue.sales_person.get_full_name() if revenue.sales_person else None
        }
        
        # 마스킹 적용
        masked_item = RevenuePermissionManager.mask_revenue_data(item_data, request.user)
        revenue_data.append(masked_item)
    
    return JsonResponse({
        'results': revenue_data,
        'total_count': paginator.count,
        'page': page,
        'per_page': per_page,
        'total_pages': paginator.num_pages,
        'user_permissions': get_user_revenue_permissions(request.user)
    })

def apply_revenue_filters(queryset, request):
    """매출 쿼리셋에 필터 적용"""
    # 날짜 범위 필터
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            queryset = queryset.filter(revenue_date__gte=start_date)
        except ValueError:
            pass
            
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            queryset = queryset.filter(revenue_date__lte=end_date)
        except ValueError:
            pass
            
    # 카테고리 필터
    category = request.GET.get('category')
    if category:
        queryset = queryset.filter(category__code=category)
        
    # 고객 필터
    client = request.GET.get('client')
    if client:
        queryset = queryset.filter(client__code=client)
        
    # 결제 상태 필터
    payment_status = request.GET.get('payment_status')
    if payment_status:
        queryset = queryset.filter(payment_status=payment_status)
        
    # 확정 여부 필터
    is_confirmed = request.GET.get('is_confirmed')
    if is_confirmed is not None:
        confirmed = is_confirmed.lower() == 'true'
        queryset = queryset.filter(is_confirmed=confirmed)
        
    # 검색어 필터
    search = request.GET.get('search')
    if search:
        queryset = queryset.filter(
            Q(project__name__icontains=search) |
            Q(client__name__icontains=search) |
            Q(description__icontains=search)
        )
    
    return queryset.order_by('-revenue_date', '-created_at')

@api_view(['GET'])
@permission_classes([RevenueReadOnlyPermission])
def revenue_analytics(request):
    """매출 분석 데이터"""
    user_role = RevenuePermissionManager.get_user_role(request.user)
    
    # 고급 분석은 관리자급만 접근 가능
    if user_role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MIDDLE_MANAGER]:
        return JsonResponse(
            {'error': '분석 데이터 조회 권한이 없습니다.'}, 
            status=403
        )
    
    queryset = RevenuePermissionManager.filter_revenue_queryset(
        RevenueRecord.objects.filter(is_confirmed=True), request.user
    )
    
    # 고객별 매출 분석
    client_stats = queryset.values('client__name', 'client__code').annotate(
        total_revenue=Sum('net_amount'),
        avg_revenue=Avg('net_amount'),
        count=Count('id')
    ).order_by('-total_revenue')[:10]
    
    # 프로젝트별 매출 분석
    project_stats = queryset.values('project__name', 'project__code').annotate(
        total_revenue=Sum('net_amount'),
        count=Count('id')
    ).order_by('-total_revenue')[:10]
    
    # 카테고리별 매출 분석
    category_stats = queryset.values('category__name', 'category__code').annotate(
        total_revenue=Sum('net_amount'),
        count=Count('id')
    ).order_by('-total_revenue')
    
    # 월별 매출 트렌드 (최근 12개월)
    monthly_trend = []
    for i in range(12):
        month_start = date.today().replace(day=1) - timedelta(days=30*i)
        month_end = (month_start.replace(month=month_start.month+1) 
                    if month_start.month < 12 
                    else month_start.replace(year=month_start.year+1, month=1))
        
        month_revenue = queryset.filter(
            revenue_date__gte=month_start,
            revenue_date__lt=month_end
        ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0')
        
        monthly_trend.append({
            'month': month_start.strftime('%Y-%m'),
            'revenue': float(month_revenue)
        })
    
    analytics_data = {
        'client_stats': list(client_stats),
        'project_stats': list(project_stats),
        'category_stats': list(category_stats),
        'monthly_trend': monthly_trend[::-1],  # 오래된 순서로 정렬
        'user_role': user_role
    }
    
    # 권한에 따른 마스킹
    if user_role == UserRole.MIDDLE_MANAGER:
        for stats_list in [analytics_data['client_stats'], analytics_data['project_stats']]:
            for stat in stats_list:
                stat = RevenuePermissionManager.mask_revenue_data(stat, request.user)
    
    return JsonResponse(analytics_data)

@api_view(['GET'])
@permission_classes([RevenueReadOnlyPermission])
def revenue_targets_progress(request):
    """매출 목표 달성 현황"""
    user_role = RevenuePermissionManager.get_user_role(request.user)
    
    # 현재 연도 목표들
    current_year = date.today().year
    targets = RevenueTarget.objects.filter(year=current_year)
    
    # 사용자 권한에 따른 목표 필터링
    if user_role == UserRole.MIDDLE_MANAGER:
        targets = targets.filter(
            Q(assigned_user=request.user) | Q(assigned_user__isnull=True)
        )
    elif user_role == UserRole.TEAM_MEMBER:
        targets = targets.filter(assigned_user=request.user)
    
    target_progress = []
    for target in targets:
        achievement_rate = target.get_achievement_rate()
        
        target_data = {
            'id': str(target.id),
            'target_type': target.get_target_type_display(),
            'period': str(target),
            'target_amount': float(target.target_amount),
            'achievement_rate': achievement_rate,
            'category': target.category.name if target.category else '전체',
            'assigned_user': target.assigned_user.get_full_name() if target.assigned_user else '전체'
        }
        
        # 마스킹 적용
        if user_role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
            target_data = RevenuePermissionManager.mask_revenue_data(target_data, request.user)
        
        target_progress.append(target_data)
    
    return JsonResponse({
        'targets': target_progress,
        'user_role': user_role
    })

@api_view(['GET'])
@permission_classes([RevenueReadOnlyPermission])
def revenue_export(request):
    """매출 데이터 내보내기"""
    user_role = RevenuePermissionManager.get_user_role(request.user)
    
    # 내보내기 권한 확인
    if user_role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MIDDLE_MANAGER]:
        return JsonResponse(
            {'error': '데이터 내보내기 권한이 없습니다.'}, 
            status=403
        )
    
    # 필터링된 쿼리셋
    queryset = RevenuePermissionManager.filter_revenue_queryset(
        RevenueRecord.objects.select_related('project', 'client', 'category'), 
        request.user
    )
    
    # 필터 적용
    queryset = apply_revenue_filters(queryset, request)
    
    # 데이터 직렬화 및 마스킹
    export_data = []
    for revenue in queryset[:1000]:  # 최대 1000개로 제한
        row_data = {
            'revenue_date': revenue.revenue_date.isoformat(),
            'project_name': revenue.project.name,
            'project_code': revenue.project.code,
            'client_name': revenue.client.name,
            'category': revenue.category.name,
            'revenue_type': revenue.get_revenue_type_display(),
            'amount': float(revenue.amount),
            'tax_amount': float(revenue.tax_amount),
            'net_amount': float(revenue.net_amount),
            'payment_status': revenue.get_payment_status_display(),
            'is_confirmed': revenue.is_confirmed,
            'sales_person': revenue.sales_person.get_full_name() if revenue.sales_person else '',
            'description': revenue.description
        }
        
        # 마스킹 적용
        masked_row = RevenuePermissionManager.mask_revenue_data(row_data, request.user)
        export_data.append(masked_row)
    
    return JsonResponse({
        'data': export_data,
        'total_count': len(export_data),
        'export_timestamp': datetime.now().isoformat(),
        'user_role': user_role,
        'filters_applied': dict(request.GET)
    })

# 에러 핸들링
def revenue_permission_denied(request, exception):
    """권한 거부 에러 처리"""
    user_role = RevenuePermissionManager.get_user_role(request.user)
    
    error_response = {
        'error': '접근 권한이 없습니다.',
        'user_role': user_role,
        'required_permissions': '관리자 또는 매출 담당자 권한이 필요합니다.',
        'timestamp': datetime.now().isoformat()
    }
    
    return JsonResponse(error_response, status=403)
