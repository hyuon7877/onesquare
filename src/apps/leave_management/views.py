from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.db.models import Q, Sum
from django.utils import timezone
from datetime import datetime, timedelta
import json

from .models import LeaveRequest, LeaveBalance, LeaveType, Holiday
from apps.auth_system.decorators import admin_required


@login_required
def leave_dashboard(request):
    """연차 관리 대시보드 뷰"""
    context = {
        'page_title': '연차 관리',
        'user': request.user,
    }
    
    # 연차 잔여일수 조회
    current_year = timezone.now().year
    try:
        balance = LeaveBalance.objects.get(
            user=request.user,
            year=current_year
        )
    except LeaveBalance.DoesNotExist:
        # 기본 연차 생성
        balance = LeaveBalance.objects.create(
            user=request.user,
            year=current_year,
            total_annual_days=15.0
        )
    
    context['balance'] = balance
    
    # 내 연차 신청 목록
    my_requests = LeaveRequest.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]
    
    context['my_requests'] = my_requests
    
    # 관리자인 경우 승인 대기 목록
    if request.user.groups.filter(name__in=['최고관리자', '중간관리자']).exists():
        pending_requests = LeaveRequest.objects.filter(
            status='pending'
        ).exclude(user=request.user).order_by('start_date')[:10]
        context['pending_requests'] = pending_requests
    
    # 공휴일 정보
    holidays = Holiday.objects.filter(
        date__year=current_year
    ).order_by('date')
    context['holidays'] = holidays
    
    return render(request, 'leave_management/dashboard.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def leave_request(request):
    """연차 신청 뷰"""
    if request.method == 'POST':
        try:
            # POST 데이터 파싱
            data = request.POST
            
            # 연차 유형 가져오기
            leave_type = get_object_or_404(LeaveType, id=data.get('leave_type_id'))
            
            # 연차 신청 생성
            leave_req = LeaveRequest.objects.create(
                user=request.user,
                leave_type=leave_type,
                start_date=data.get('start_date'),
                end_date=data.get('end_date'),
                reason=data.get('reason'),
                emergency_contact=data.get('emergency_contact', ''),
                is_half_day_start=data.get('is_half_day_start') == 'true',
                is_half_day_end=data.get('is_half_day_end') == 'true',
            )
            
            # 첨부파일 처리
            if 'attachment' in request.FILES:
                leave_req.attachment = request.FILES['attachment']
                leave_req.save()
            
            messages.success(request, '연차 신청이 완료되었습니다.')
            
            # AJAX 요청인 경우 JSON 응답
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': '연차 신청이 완료되었습니다.',
                    'request_id': leave_req.id
                })
            
            return redirect('leave_management:dashboard')
            
        except Exception as e:
            messages.error(request, f'연차 신청 중 오류가 발생했습니다: {str(e)}')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                }, status=400)
    
    # GET 요청 - 신청 폼 표시
    context = {
        'page_title': '연차 신청',
        'leave_types': LeaveType.objects.all(),
        'balance': LeaveBalance.objects.get_or_create(
            user=request.user,
            year=timezone.now().year
        )[0]
    }
    
    return render(request, 'leave_management/request_form.html', context)


@login_required
@admin_required
@require_http_methods(["POST"])
def approve_leave(request, request_id):
    """연차 승인 처리"""
    try:
        leave_req = get_object_or_404(LeaveRequest, id=request_id)
        
        if leave_req.status != 'pending':
            raise ValueError('대기중인 신청만 승인할 수 있습니다.')
        
        # 승인 처리
        leave_req.approve(request.user)
        
        messages.success(request, f'{leave_req.user.username}님의 연차가 승인되었습니다.')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': '연차가 승인되었습니다.'
            })
        
        return redirect('leave_management:dashboard')
        
    except Exception as e:
        messages.error(request, f'승인 처리 중 오류: {str(e)}')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
        
        return redirect('leave_management:dashboard')


@login_required
@admin_required
@require_http_methods(["POST"])
def reject_leave(request, request_id):
    """연차 반려 처리"""
    try:
        leave_req = get_object_or_404(LeaveRequest, id=request_id)
        
        if leave_req.status != 'pending':
            raise ValueError('대기중인 신청만 반려할 수 있습니다.')
        
        # 반려 사유
        reason = request.POST.get('rejection_reason', '관리자 반려')
        
        # 반려 처리
        leave_req.reject(request.user, reason)
        
        messages.success(request, f'{leave_req.user.username}님의 연차가 반려되었습니다.')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': '연차가 반려되었습니다.'
            })
        
        return redirect('leave_management:dashboard')
        
    except Exception as e:
        messages.error(request, f'반려 처리 중 오류: {str(e)}')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
        
        return redirect('leave_management:dashboard')


@login_required
@require_http_methods(["POST"])
def cancel_leave(request, request_id):
    """연차 취소 처리"""
    try:
        leave_req = get_object_or_404(LeaveRequest, id=request_id, user=request.user)
        
        if leave_req.status == 'cancelled':
            raise ValueError('이미 취소된 신청입니다.')
        
        # 취소 처리
        leave_req.cancel()
        
        messages.success(request, '연차 신청이 취소되었습니다.')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': '연차 신청이 취소되었습니다.'
            })
        
        return redirect('leave_management:dashboard')
        
    except Exception as e:
        messages.error(request, f'취소 처리 중 오류: {str(e)}')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
        
        return redirect('leave_management:dashboard')


@login_required
def api_leave_calendar(request):
    """캘린더용 연차 데이터 API"""
    start = request.GET.get('start')
    end = request.GET.get('end')
    
    # 날짜 범위 내 연차 조회
    leaves = LeaveRequest.objects.filter(
        Q(start_date__lte=end) & Q(end_date__gte=start),
        status__in=['pending', 'approved']
    )
    
    # 권한에 따른 필터링
    if not request.user.groups.filter(name__in=['최고관리자', '중간관리자']).exists():
        # 일반 사용자는 본인 연차만 조회
        leaves = leaves.filter(user=request.user)
    
    # 캘린더 이벤트 형식으로 변환
    events = []
    for leave in leaves:
        color = '#28a745' if leave.status == 'approved' else '#ffc107'
        events.append({
            'id': leave.id,
            'title': f'{leave.user.username} - {leave.leave_type.get_name_display()}',
            'start': leave.start_date.isoformat(),
            'end': (leave.end_date + timedelta(days=1)).isoformat(),
            'backgroundColor': color,
            'borderColor': color,
            'extendedProps': {
                'user': leave.user.username,
                'status': leave.status,
                'reason': leave.reason,
                'total_days': str(leave.total_days)
            }
        })
    
    # 공휴일 추가
    holidays = Holiday.objects.filter(
        date__gte=start,
        date__lte=end
    )
    
    for holiday in holidays:
        events.append({
            'id': f'holiday_{holiday.id}',
            'title': holiday.name,
            'start': holiday.date.isoformat(),
            'allDay': True,
            'backgroundColor': '#dc3545',
            'borderColor': '#dc3545',
            'display': 'background'
        })
    
    return JsonResponse(events, safe=False)


@login_required
def api_leave_balance(request):
    """연차 잔여일수 조회 API"""
    year = request.GET.get('year', timezone.now().year)
    
    try:
        balance = LeaveBalance.objects.get(
            user=request.user,
            year=year
        )
        
        data = {
            'total': float(balance.total_annual_days),
            'used': float(balance.used_annual_days),
            'remaining': float(balance.remaining_annual_days),
            'carry_over': float(balance.carry_over_days)
        }
        
    except LeaveBalance.DoesNotExist:
        data = {
            'total': 0,
            'used': 0,
            'remaining': 0,
            'carry_over': 0
        }
    
    return JsonResponse(data)
