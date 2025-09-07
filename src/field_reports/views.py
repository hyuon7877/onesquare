from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from .models import FieldReport, ReportAttachment
import json
import os


@login_required
def report_list(request):
    """현장 리포트 목록"""
    reports = FieldReport.objects.filter(author=request.user)
    
    # 검색 기능
    query = request.GET.get('q')
    if query:
        reports = reports.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(project_name__icontains=query) |
            Q(site_name__icontains=query)
        )
    
    # 필터링
    status_filter = request.GET.get('status')
    if status_filter:
        reports = reports.filter(status=status_filter)
    
    report_type = request.GET.get('type')
    if report_type:
        reports = reports.filter(report_type=report_type)
    
    # 페이지네이션
    paginator = Paginator(reports, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'query': query,
        'status_filter': status_filter,
        'report_type': report_type,
    }
    return render(request, 'field_reports/report_list.html', context)


@login_required
def report_create(request):
    """리포트 작성"""
    if request.method == 'POST':
        # 폼 데이터 처리
        report = FieldReport(
            author=request.user,
            title=request.POST.get('title'),
            report_type=request.POST.get('report_type', 'daily'),
            content=request.POST.get('content'),
            project_name=request.POST.get('project_name'),
            site_name=request.POST.get('site_name'),
            contractor=request.POST.get('contractor', ''),
            weather=request.POST.get('weather', ''),
            temperature=request.POST.get('temperature', ''),
            workers_count=int(request.POST.get('workers_count', 0)),
            attendees=request.POST.get('attendees', ''),
            location_address=request.POST.get('location_address', ''),
            status=request.POST.get('status', 'draft'),
        )
        
        # GPS 위치 정보
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        if latitude and longitude:
            report.latitude = float(latitude)
            report.longitude = float(longitude)
        
        # 오프라인 여부
        report.is_offline = request.POST.get('is_offline') == 'true'
        
        # 제출 시간 기록
        if report.status == 'submitted':
            report.submitted_at = timezone.now()
        
        report.save()
        
        # 파일 첨부 처리
        if request.FILES:
            for file in request.FILES.getlist('attachments'):
                attachment = ReportAttachment(
                    report=report,
                    file=file,
                    file_name=file.name,
                    file_size=file.size,
                )
                # 파일 타입 결정
                ext = os.path.splitext(file.name)[1].lower()
                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                    attachment.file_type = 'image'
                elif ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx']:
                    attachment.file_type = 'document'
                elif ext in ['.mp4', '.avi', '.mov', '.wmv']:
                    attachment.file_type = 'video'
                else:
                    attachment.file_type = 'other'
                
                attachment.save()
        
        messages.success(request, '리포트가 성공적으로 작성되었습니다.')
        
        # 제출 상태인 경우 리스트로, 임시저장인 경우 상세 페이지로
        if report.status == 'submitted':
            return redirect('field_reports:report_list')
        else:
            return redirect('field_reports:report_detail', pk=report.pk)
    
    # GET 요청 - 폼 표시
    context = {
        'report_types': FieldReport.REPORT_TYPE_CHOICES,
    }
    return render(request, 'field_reports/report_form.html', context)


@login_required
def report_detail(request, pk):
    """리포트 상세 보기"""
    report = get_object_or_404(FieldReport, pk=pk)
    
    # 권한 확인 (작성자 또는 관리자만 볼 수 있음)
    if report.author != request.user and not request.user.is_staff:
        messages.error(request, '이 리포트를 볼 권한이 없습니다.')
        return redirect('field_reports:report_list')
    
    attachments = report.attachments.all()
    
    context = {
        'report': report,
        'attachments': attachments,
    }
    return render(request, 'field_reports/report_detail.html', context)


@login_required
def report_edit(request, pk):
    """리포트 수정"""
    report = get_object_or_404(FieldReport, pk=pk)
    
    # 작성자만 수정 가능
    if report.author != request.user:
        messages.error(request, '이 리포트를 수정할 권한이 없습니다.')
        return redirect('field_reports:report_detail', pk=pk)
    
    # 이미 제출된 리포트는 수정 불가
    if report.status in ['submitted', 'approved']:
        messages.error(request, '제출된 리포트는 수정할 수 없습니다.')
        return redirect('field_reports:report_detail', pk=pk)
    
    if request.method == 'POST':
        report.title = request.POST.get('title')
        report.report_type = request.POST.get('report_type', 'daily')
        report.content = request.POST.get('content')
        report.project_name = request.POST.get('project_name')
        report.site_name = request.POST.get('site_name')
        report.contractor = request.POST.get('contractor', '')
        report.weather = request.POST.get('weather', '')
        report.temperature = request.POST.get('temperature', '')
        report.workers_count = int(request.POST.get('workers_count', 0))
        report.attendees = request.POST.get('attendees', '')
        report.location_address = request.POST.get('location_address', '')
        report.status = request.POST.get('status', 'draft')
        
        # GPS 위치 정보
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        if latitude and longitude:
            report.latitude = float(latitude)
            report.longitude = float(longitude)
        
        # 제출 시간 기록
        if report.status == 'submitted' and not report.submitted_at:
            report.submitted_at = timezone.now()
        
        report.save()
        
        # 상태에 따른 메시지와 리다이렉트
        if report.status == 'submitted':
            messages.success(request, '리포트가 제출되었습니다.')
            return redirect('field_reports:report_list')
        else:
            messages.success(request, '리포트가 수정되었습니다.')
            return redirect('field_reports:report_detail', pk=pk)
    
    context = {
        'report': report,
        'report_types': FieldReport.REPORT_TYPE_CHOICES,
        'attachments': report.attachments.all(),
    }
    return render(request, 'field_reports/report_form.html', context)


@login_required
def report_delete(request, pk):
    """리포트 삭제"""
    report = get_object_or_404(FieldReport, pk=pk)
    
    # 작성자 또는 관리자만 삭제 가능
    if report.author != request.user and not request.user.is_staff:
        messages.error(request, '삭제 권한이 없습니다.')
        return redirect('field_reports:report_detail', pk=pk)
    
    # 승인된 리포트는 삭제 불가
    if report.status == 'approved':
        messages.error(request, '승인된 리포트는 삭제할 수 없습니다.')
        return redirect('field_reports:report_detail', pk=pk)
    
    report.delete()
    messages.success(request, '리포트가 삭제되었습니다.')
    return redirect('field_reports:report_list')


@login_required
@require_http_methods(["POST"])
def upload_attachment(request, pk):
    """파일 첨부 업로드 (AJAX)"""
    report = get_object_or_404(FieldReport, pk=pk)
    
    if report.author != request.user:
        return JsonResponse({'error': '권한이 없습니다.'}, status=403)
    
    if 'file' not in request.FILES:
        return JsonResponse({'error': '파일이 없습니다.'}, status=400)
    
    file = request.FILES['file']
    
    attachment = ReportAttachment(
        report=report,
        file=file,
        file_name=file.name,
        file_size=file.size,
        description=request.POST.get('description', '')
    )
    
    # 파일 타입 결정
    ext = os.path.splitext(file.name)[1].lower()
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
        attachment.file_type = 'image'
    elif ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx']:
        attachment.file_type = 'document'
    elif ext in ['.mp4', '.avi', '.mov', '.wmv']:
        attachment.file_type = 'video'
    else:
        attachment.file_type = 'other'
    
    attachment.save()
    
    return JsonResponse({
        'success': True,
        'attachment': {
            'id': attachment.id,
            'file_name': attachment.file_name,
            'file_type': attachment.file_type,
            'file_url': attachment.file.url,
            'uploaded_at': attachment.uploaded_at.isoformat(),
        }
    })


@login_required
@require_http_methods(["POST"])
def save_offline_report(request):
    """오프라인 리포트 저장 (PWA)"""
    try:
        data = json.loads(request.body)
        
        report = FieldReport(
            author=request.user,
            title=data.get('title'),
            report_type=data.get('report_type', 'daily'),
            content=data.get('content'),
            project_name=data.get('project_name'),
            site_name=data.get('site_name'),
            contractor=data.get('contractor', ''),
            weather=data.get('weather', ''),
            temperature=data.get('temperature', ''),
            workers_count=data.get('workers_count', 0),
            attendees=data.get('attendees', ''),
            location_address=data.get('location_address', ''),
            status='draft',
            is_offline=True,
            sync_status='pending',
        )
        
        # GPS 정보
        if 'latitude' in data and 'longitude' in data:
            report.latitude = data['latitude']
            report.longitude = data['longitude']
        
        # 메타데이터 (오프라인 생성 시간 등)
        report.metadata = {
            'offline_created': data.get('offline_created'),
            'device_info': data.get('device_info', {}),
        }
        
        report.save()
        
        return JsonResponse({
            'success': True,
            'report_id': report.id,
            'message': '오프라인 리포트가 저장되었습니다.'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def sync_reports(request):
    """오프라인 리포트 동기화"""
    if request.method == 'POST':
        # 동기화 대기 중인 리포트들
        pending_reports = FieldReport.objects.filter(
            author=request.user,
            is_offline=True,
            sync_status='pending'
        )
        
        synced_count = 0
        for report in pending_reports:
            # TODO: Notion API와 동기화 로직 구현
            report.sync_status = 'synced'
            report.notion_sync_at = timezone.now()
            report.save()
            synced_count += 1
        
        return JsonResponse({
            'success': True,
            'synced_count': synced_count,
            'message': f'{synced_count}개의 리포트가 동기화되었습니다.'
        })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)