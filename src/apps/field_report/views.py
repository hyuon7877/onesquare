"""
OneSquare 현장 리포트 시스템 뷰

파트너 전용 현장 작업 관리 및 리포트 기능
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.conf import settings

import json
import uuid
from datetime import datetime, timedelta
from PIL import Image, ExifTags
import io
import base64

from .models import (
    FieldSite, WorkSession, TaskChecklist, WorkReport, 
    ReportPhoto, InventoryItem, InventoryCheck
)


# ================================
# 메인 대시보드 뷰
# ================================

@login_required
def field_dashboard(request):
    """현장 리포트 메인 대시보드 (모바일 최적화)"""
    user = request.user
    
    # 현재 활성 세션 확인
    active_session = WorkSession.objects.filter(
        user=user, 
        status__in=['started', 'paused']
    ).first()
    
    # 최근 작업 현장
    recent_sites = FieldSite.objects.filter(
        worksession__user=user,
        is_active=True
    ).distinct().order_by('-worksession__start_time')[:5]
    
    # 오늘 업무 통계
    today = timezone.now().date()
    today_sessions = WorkSession.objects.filter(
        user=user,
        start_time__date=today
    )
    
    today_stats = {
        'total_sessions': today_sessions.count(),
        'total_hours': sum((s.duration_hours for s in today_sessions), 0),
        'active_session': active_session
    }
    
    # 대기 중인 리포트
    pending_reports = WorkReport.objects.filter(
        session__user=user,
        status='draft'
    ).count()
    
    context = {
        'active_session': active_session,
        'recent_sites': recent_sites,
        'today_stats': today_stats,
        'pending_reports': pending_reports,
        'is_mobile': request.META.get('HTTP_USER_AGENT', '').lower().find('mobile') != -1
    }
    
    return render(request, 'field_report/dashboard.html', context)


# ================================
# 업무 세션 관리
# ================================

@login_required
@require_http_methods(["POST"])
def start_work_session(request):
    """업무 시작"""
    try:
        data = json.loads(request.body)
        site_id = data.get('site_id')
        
        # 기존 활성 세션 확인
        active_session = WorkSession.objects.filter(
            user=request.user,
            status__in=['started', 'paused']
        ).first()
        
        if active_session:
            return JsonResponse({
                'error': '이미 진행 중인 업무가 있습니다.',
                'active_session_id': str(active_session.id)
            }, status=400)
        
        # 현장 정보 확인
        site = get_object_or_404(FieldSite, id=site_id)
        
        # GPS 위치 정보
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        accuracy = data.get('accuracy')
        
        # 새 세션 생성
        session = WorkSession.objects.create(
            user=request.user,
            site=site,
            start_time=timezone.now(),
            start_latitude=latitude,
            start_longitude=longitude,
            location_accuracy=accuracy,
            location_verified=True if latitude and longitude else False,
            status='started'
        )
        
        return JsonResponse({
            'success': True,
            'session_id': str(session.id),
            'site_name': site.name,
            'start_time': session.start_time.isoformat(),
            'message': f'{site.name}에서 업무를 시작했습니다.'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def end_work_session(request, session_id):
    """업무 종료"""
    try:
        session = get_object_or_404(
            WorkSession, 
            id=session_id, 
            user=request.user,
            status__in=['started', 'paused']
        )
        
        data = json.loads(request.body)
        
        # GPS 위치 정보
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        notes = data.get('notes', '')
        
        # 세션 종료
        session.end_time = timezone.now()
        session.end_latitude = latitude
        session.end_longitude = longitude
        session.notes = notes
        session.status = 'completed'
        session.save()
        
        return JsonResponse({
            'success': True,
            'duration_hours': session.duration_hours,
            'message': f'{session.site.name} 업무가 완료되었습니다.'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def pause_work_session(request, session_id):
    """업무 일시 중지"""
    try:
        session = get_object_or_404(
            WorkSession, 
            id=session_id, 
            user=request.user,
            status='started'
        )
        
        session.status = 'paused'
        session.save()
        
        return JsonResponse({
            'success': True,
            'message': '업무가 일시 중지되었습니다.'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def resume_work_session(request, session_id):
    """업무 재개"""
    try:
        session = get_object_or_404(
            WorkSession, 
            id=session_id, 
            user=request.user,
            status='paused'
        )
        
        session.status = 'resumed'
        session.save()
        
        return JsonResponse({
            'success': True,
            'message': '업무가 재개되었습니다.'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ================================
# 체크리스트 관리
# ================================

@login_required
def checklist_view(request, session_id):
    """체크리스트 작업 페이지"""
    session = get_object_or_404(
        WorkSession, 
        id=session_id, 
        user=request.user
    )
    
    # 해당 현장의 체크리스트 조회
    checklists = TaskChecklist.objects.filter(
        Q(site=session.site) | Q(site__isnull=True),
        is_active=True
    ).order_by('priority')
    
    # 기존 리포트가 있는지 확인
    existing_report = WorkReport.objects.filter(session=session).first()
    
    context = {
        'session': session,
        'checklists': checklists,
        'existing_report': existing_report
    }
    
    return render(request, 'field_report/checklist.html', context)


@login_required
@require_http_methods(["POST"])
def save_checklist_progress(request, session_id):
    """체크리스트 진행상황 저장"""
    try:
        session = get_object_or_404(
            WorkSession, 
            id=session_id, 
            user=request.user
        )
        
        data = json.loads(request.body)
        checklist_id = data.get('checklist_id')
        checklist_status = data.get('checklist_status', {})
        title = data.get('title', f'{session.site.name} 작업 리포트')
        notes = data.get('additional_notes', '')
        
        checklist = get_object_or_404(TaskChecklist, id=checklist_id)
        
        # 리포트 생성 또는 업데이트
        report, created = WorkReport.objects.get_or_create(
            session=session,
            defaults={
                'checklist': checklist,
                'title': title,
                'checklist_status': checklist_status,
                'additional_notes': notes
            }
        )
        
        if not created:
            report.checklist_status = checklist_status
            report.additional_notes = notes
            report.save()
        
        # 완료율 업데이트
        report.update_completion_percentage()
        report.save()
        
        return JsonResponse({
            'success': True,
            'report_id': str(report.id),
            'completion_percentage': report.completion_percentage,
            'message': '진행상황이 저장되었습니다.'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ================================
# 사진 업로드 및 압축
# ================================

@login_required
@require_http_methods(["POST"])
def upload_report_photos(request, report_id):
    """리포트 사진 업로드 및 자동 압축"""
    try:
        report = get_object_or_404(
            WorkReport, 
            id=report_id, 
            session__user=request.user
        )
        
        uploaded_photos = []
        
        for key, file in request.FILES.items():
            if key.startswith('photo_'):
                # 사진 메타데이터
                photo_type = request.POST.get(f'{key}_type', 'other')
                caption = request.POST.get(f'{key}_caption', '')
                
                # 리포트 사진 객체 생성
                photo = ReportPhoto.objects.create(
                    report=report,
                    original_image=file,
                    photo_type=photo_type,
                    caption=caption,
                    original_file_size=file.size
                )
                
                # 이미지 압축 처리
                compress_image_async(photo.id)
                
                uploaded_photos.append({
                    'id': str(photo.id),
                    'type': photo.get_photo_type_display(),
                    'caption': photo.caption,
                    'original_size': photo.original_file_size
                })
        
        return JsonResponse({
            'success': True,
            'uploaded_count': len(uploaded_photos),
            'photos': uploaded_photos,
            'message': f'{len(uploaded_photos)}장의 사진이 업로드되었습니다.'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def compress_image_async(photo_id):
    """비동기 이미지 압축 처리 (실제로는 백그라운드 작업으로 처리하는 것을 권장)"""
    try:
        photo = ReportPhoto.objects.get(id=photo_id)
        
        # PIL을 사용한 이미지 압축
        with Image.open(photo.original_image.path) as img:
            # EXIF 데이터에서 GPS 정보 추출
            extract_gps_from_exif(img, photo)
            
            # 이미지 크기 조정 (최대 1920x1080)
            max_size = (1920, 1080)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # 압축된 이미지 저장
            compressed_path = photo.original_image.path.replace('/original/', '/compressed/')
            img.save(compressed_path, 'JPEG', quality=85, optimize=True)
            
            # 썸네일 생성 (300x300)
            thumbnail_size = (300, 300)
            thumbnail = img.copy()
            thumbnail.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
            
            thumbnail_path = photo.original_image.path.replace('/original/', '/thumbnails/')
            thumbnail.save(thumbnail_path, 'JPEG', quality=80)
            
            # 압축 정보 업데이트
            import os
            photo.compressed_file_size = os.path.getsize(compressed_path)
            photo.save()
            
    except Exception as e:
        print(f"Image compression failed for photo {photo_id}: {e}")


def extract_gps_from_exif(img, photo):
    """EXIF 데이터에서 GPS 정보 추출"""
    try:
        exif = img._getexif()
        if exif:
            for tag, value in exif.items():
                tag_name = ExifTags.TAGS.get(tag, tag)
                
                if tag_name == 'GPSInfo':
                    gps_data = value
                    lat = get_decimal_coordinates(
                        gps_data.get(2), gps_data.get(1)
                    )
                    lon = get_decimal_coordinates(
                        gps_data.get(4), gps_data.get(3)
                    )
                    
                    if lat and lon:
                        photo.latitude = lat
                        photo.longitude = lon
                
                elif tag_name == 'DateTime':
                    try:
                        photo.taken_at = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                    except ValueError:
                        pass
    except Exception:
        pass


def get_decimal_coordinates(gps_coords, gps_hemisphere):
    """GPS 좌표를 십진법으로 변환"""
    if not gps_coords or not gps_hemisphere:
        return None
    
    try:
        d, m, s = gps_coords
        decimal = float(d) + float(m)/60 + float(s)/3600
        
        if gps_hemisphere in ['S', 'W']:
            decimal = -decimal
            
        return decimal
    except:
        return None


# ================================
# 재고 관리
# ================================

@login_required
def inventory_check_view(request, report_id):
    """재고 체크 페이지"""
    report = get_object_or_404(
        WorkReport, 
        id=report_id, 
        session__user=request.user
    )
    
    # 활성 재고 항목 조회
    inventory_items = InventoryItem.objects.filter(is_active=True).order_by('category', 'name')
    
    # 기존 재고 체크 내역
    existing_checks = InventoryCheck.objects.filter(report=report)
    existing_checks_dict = {check.item_id: check for check in existing_checks}
    
    context = {
        'report': report,
        'inventory_items': inventory_items,
        'existing_checks': existing_checks_dict
    }
    
    return render(request, 'field_report/inventory_check.html', context)


@login_required
@require_http_methods(["POST"])
def save_inventory_check(request, report_id):
    """재고 체크 결과 저장"""
    try:
        report = get_object_or_404(
            WorkReport, 
            id=report_id, 
            session__user=request.user
        )
        
        data = json.loads(request.body)
        inventory_data = data.get('inventory_checks', {})
        
        saved_checks = []
        
        for item_id, check_data in inventory_data.items():
            item = get_object_or_404(InventoryItem, id=item_id)
            
            # 재고 체크 생성 또는 업데이트
            inventory_check, created = InventoryCheck.objects.update_or_create(
                report=report,
                item=item,
                defaults={
                    'current_quantity': check_data.get('current_quantity', 0),
                    'required_quantity': check_data.get('required_quantity'),
                    'notes': check_data.get('notes', '')
                }
            )
            
            saved_checks.append({
                'item_name': item.name,
                'current_quantity': inventory_check.current_quantity,
                'is_sufficient': inventory_check.is_sufficient,
                'needs_replenishment': inventory_check.needs_replenishment
            })
        
        return JsonResponse({
            'success': True,
            'saved_checks': saved_checks,
            'message': f'{len(saved_checks)}개 항목의 재고가 체크되었습니다.'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ================================
# API 엔드포인트
# ================================

@login_required
def api_field_sites(request):
    """현장 목록 API"""
    sites = FieldSite.objects.filter(is_active=True).values(
        'id', 'name', 'address', 'latitude', 'longitude'
    )
    
    return JsonResponse({
        'sites': list(sites)
    })


@login_required
def api_work_session_status(request):
    """현재 업무 세션 상태 API"""
    active_session = WorkSession.objects.filter(
        user=request.user,
        status__in=['started', 'paused', 'resumed']
    ).first()
    
    if active_session:
        return JsonResponse({
            'has_active_session': True,
            'session_id': str(active_session.id),
            'site_name': active_session.site.name,
            'status': active_session.status,
            'start_time': active_session.start_time.isoformat(),
            'duration_hours': active_session.duration_hours
        })
    else:
        return JsonResponse({
            'has_active_session': False
        })


@login_required
def api_reports_summary(request):
    """리포트 요약 통계 API"""
    user_reports = WorkReport.objects.filter(session__user=request.user)
    
    # 최근 7일 통계
    last_week = timezone.now() - timedelta(days=7)
    recent_reports = user_reports.filter(created_at__gte=last_week)
    
    summary = {
        'total_reports': user_reports.count(),
        'recent_reports': recent_reports.count(),
        'draft_reports': user_reports.filter(status='draft').count(),
        'approved_reports': user_reports.filter(status='approved').count(),
        'average_completion': user_reports.aggregate(
            avg_completion=Avg('completion_percentage')
        )['avg_completion'] or 0
    }
    
    return JsonResponse(summary)


@login_required
def photo_upload_view(request):
    """사진 업로드 페이지"""
    return render(request, 'field_report/photo_upload.html')


@login_required
def inventory_check_view(request):
    """재고 체크 페이지"""
    return render(request, 'field_report/inventory_check.html')