"""
OneSquare 업무 시간 추적 전용 뷰
GPS 위치 검증 및 실시간 시간 추적 기능
"""

from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
from django.core.serializers.json import DjangoJSONEncoder

import json
import math
from datetime import datetime, timedelta
from decimal import Decimal

from .models import FieldSite, WorkSession


class TimeTrackingAPI:
    """업무 시간 추적 API 클래스"""
    
    @staticmethod
    def calculate_distance(lat1, lon1, lat2, lon2):
        """두 GPS 좌표 간의 거리를 계산 (Haversine 공식)"""
        if not all([lat1, lon1, lat2, lon2]):
            return float('inf')
        
        # 지구 반지름 (미터)
        R = 6371000
        
        # 라디안으로 변환
        lat1_rad = math.radians(float(lat1))
        lon1_rad = math.radians(float(lon1))
        lat2_rad = math.radians(float(lat2))
        lon2_rad = math.radians(float(lon2))
        
        # 차이 계산
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        # Haversine 공식
        a = (math.sin(dlat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    @staticmethod
    def verify_location(user_lat, user_lon, site_lat, site_lon, tolerance=200):
        """위치 검증"""
        if not all([user_lat, user_lon, site_lat, site_lon]):
            return {
                'verified': False,
                'distance': None,
                'reason': '위치 정보가 불완전합니다.'
            }
        
        distance = TimeTrackingAPI.calculate_distance(
            user_lat, user_lon, site_lat, site_lon
        )
        
        verified = distance <= tolerance
        
        return {
            'verified': verified,
            'distance': round(distance),
            'tolerance': tolerance,
            'reason': (
                '위치가 확인되었습니다.' if verified 
                else f'현장으로부터 {round(distance)}m 떨어져 있습니다. (허용범위: {tolerance}m)'
            )
        }


@login_required
def time_tracker_view(request):
    """업무 시간 추적 페이지"""
    from django.shortcuts import render
    
    context = {
        'user': request.user,
        'current_time': timezone.now(),
        'is_mobile': 'mobile' in request.META.get('HTTP_USER_AGENT', '').lower()
    }
    
    return render(request, 'field_report/time_tracker.html', context)


@login_required
@require_http_methods(["GET"])
def get_available_sites(request):
    """사용 가능한 현장 목록 조회"""
    sites = FieldSite.objects.filter(is_active=True).order_by('name')
    
    sites_data = []
    for site in sites:
        sites_data.append({
            'id': str(site.id),
            'name': site.name,
            'address': site.address,
            'latitude': float(site.latitude) if site.latitude else None,
            'longitude': float(site.longitude) if site.longitude else None,
            'description': site.description
        })
    
    return JsonResponse({
        'success': True,
        'sites': sites_data
    })


@login_required
@require_http_methods(["GET"])
def get_current_session(request):
    """현재 활성 세션 상태 조회"""
    active_session = WorkSession.objects.filter(
        user=request.user,
        status__in=['started', 'paused']
    ).select_related('site').first()
    
    if not active_session:
        return JsonResponse({
            'success': True,
            'has_active_session': False
        })
    
    session_data = {
        'id': str(active_session.id),
        'site_id': str(active_session.site.id),
        'site_name': active_session.site.name,
        'status': active_session.status,
        'start_time': active_session.start_time.isoformat(),
        'duration_hours': active_session.duration_hours,
        'start_latitude': float(active_session.start_latitude) if active_session.start_latitude else None,
        'start_longitude': float(active_session.start_longitude) if active_session.start_longitude else None,
        'location_verified': active_session.location_verified,
        'location_accuracy': active_session.location_accuracy
    }
    
    return JsonResponse({
        'success': True,
        'has_active_session': True,
        'session': session_data
    })


@login_required
@require_http_methods(["POST"])
def start_work(request):
    """업무 시작"""
    try:
        data = json.loads(request.body)
        site_id = data.get('site_id')
        start_latitude = data.get('start_latitude')
        start_longitude = data.get('start_longitude')
        location_accuracy = data.get('location_accuracy')
        
        # 입력 검증
        if not site_id:
            return JsonResponse({
                'success': False,
                'message': '현장을 선택해주세요.'
            }, status=400)
        
        # 현장 존재 확인
        try:
            site = FieldSite.objects.get(id=site_id, is_active=True)
        except FieldSite.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '선택한 현장을 찾을 수 없습니다.'
            }, status=404)
        
        # 기존 활성 세션 확인
        existing_session = WorkSession.objects.filter(
            user=request.user,
            status__in=['started', 'paused']
        ).first()
        
        if existing_session:
            return JsonResponse({
                'success': False,
                'message': f'이미 진행 중인 업무가 있습니다. ({existing_session.site.name})'
            }, status=400)
        
        # 위치 검증 (선택적)
        location_verified = False
        verification_result = None
        
        if start_latitude and start_longitude and site.latitude and site.longitude:
            verification_result = TimeTrackingAPI.verify_location(
                start_latitude, start_longitude,
                site.latitude, site.longitude
            )
            location_verified = verification_result['verified']
        
        # 새 세션 생성
        session = WorkSession.objects.create(
            user=request.user,
            site=site,
            start_time=timezone.now(),
            status='started',
            start_latitude=Decimal(str(start_latitude)) if start_latitude else None,
            start_longitude=Decimal(str(start_longitude)) if start_longitude else None,
            location_verified=location_verified,
            location_accuracy=location_accuracy
        )
        
        # 응답 데이터 구성
        response_data = {
            'success': True,
            'message': '업무를 시작했습니다.',
            'session': {
                'id': str(session.id),
                'site_id': str(site.id),
                'site_name': site.name,
                'start_time': session.start_time.isoformat(),
                'status': session.status,
                'location_verified': location_verified
            }
        }
        
        if verification_result:
            response_data['location_verification'] = verification_result
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '잘못된 요청 형식입니다.'
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'업무 시작 중 오류가 발생했습니다: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def end_work(request):
    """업무 종료"""
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        end_latitude = data.get('end_latitude')
        end_longitude = data.get('end_longitude')
        location_accuracy = data.get('location_accuracy')
        notes = data.get('notes', '')
        
        # 세션 확인
        try:
            session = WorkSession.objects.get(
                id=session_id,
                user=request.user,
                status__in=['started', 'paused']
            )
        except WorkSession.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '진행 중인 업무를 찾을 수 없습니다.'
            }, status=404)
        
        # 종료 시간 및 위치 정보 업데이트
        session.end_time = timezone.now()
        session.status = 'completed'
        session.notes = notes
        
        if end_latitude and end_longitude:
            session.end_latitude = Decimal(str(end_latitude))
            session.end_longitude = Decimal(str(end_longitude))
            
            # 종료 위치 검증 (선택적)
            if session.site.latitude and session.site.longitude:
                verification_result = TimeTrackingAPI.verify_location(
                    end_latitude, end_longitude,
                    session.site.latitude, session.site.longitude
                )
                # 시작할 때 검증되었거나 종료 시 검증되면 위치 검증 완료로 처리
                if not session.location_verified and verification_result['verified']:
                    session.location_verified = True
        
        if location_accuracy:
            session.location_accuracy = min(
                session.location_accuracy or float('inf'),
                location_accuracy
            )
        
        session.save()
        
        # 업무 시간 계산
        duration = session.duration
        duration_str = f"{int(duration.total_seconds() // 3600)}시간 {int((duration.total_seconds() % 3600) // 60)}분"
        
        return JsonResponse({
            'success': True,
            'message': '업무를 종료했습니다.',
            'session': {
                'id': str(session.id),
                'duration': duration_str,
                'duration_hours': session.duration_hours,
                'end_time': session.end_time.isoformat()
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '잘못된 요청 형식입니다.'
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'업무 종료 중 오류가 발생했습니다: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def pause_work(request):
    """업무 일시중지"""
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        # 세션 확인
        try:
            session = WorkSession.objects.get(
                id=session_id,
                user=request.user,
                status='started'
            )
        except WorkSession.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '진행 중인 업무를 찾을 수 없습니다.'
            }, status=404)
        
        session.status = 'paused'
        session.save()
        
        return JsonResponse({
            'success': True,
            'message': '업무를 일시중지했습니다.',
            'session': {
                'id': str(session.id),
                'status': session.status
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'업무 일시중지 중 오류가 발생했습니다: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def resume_work(request):
    """업무 재개"""
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        # 세션 확인
        try:
            session = WorkSession.objects.get(
                id=session_id,
                user=request.user,
                status='paused'
            )
        except WorkSession.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '일시중지된 업무를 찾을 수 없습니다.'
            }, status=404)
        
        session.status = 'resumed'  # 또는 'started'로 변경
        session.save()
        
        return JsonResponse({
            'success': True,
            'message': '업무를 재개했습니다.',
            'session': {
                'id': str(session.id),
                'status': session.status
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'업무 재개 중 오류가 발생했습니다: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_recent_sessions(request):
    """최근 업무 세션 목록"""
    limit = int(request.GET.get('limit', 10))
    
    sessions = WorkSession.objects.filter(
        user=request.user
    ).select_related('site').order_by('-start_time')[:limit]
    
    sessions_data = []
    for session in sessions:
        session_data = {
            'id': str(session.id),
            'site_id': str(session.site.id),
            'site_name': session.site.name,
            'status': session.status,
            'status_display': session.get_status_display(),
            'start_time': session.start_time.isoformat(),
            'end_time': session.end_time.isoformat() if session.end_time else None,
            'duration_hours': session.duration_hours,
            'location_verified': session.location_verified,
            'notes': session.notes
        }
        sessions_data.append(session_data)
    
    return JsonResponse({
        'success': True,
        'sessions': sessions_data
    })


@login_required
@require_http_methods(["POST"])
def verify_location(request):
    """위치 검증 API"""
    try:
        data = json.loads(request.body)
        user_latitude = data.get('latitude')
        user_longitude = data.get('longitude')
        site_id = data.get('site_id')
        tolerance = data.get('tolerance', 200)
        
        if not all([user_latitude, user_longitude, site_id]):
            return JsonResponse({
                'success': False,
                'message': '필수 매개변수가 누락되었습니다.'
            }, status=400)
        
        # 현장 정보 조회
        try:
            site = FieldSite.objects.get(id=site_id, is_active=True)
        except FieldSite.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '현장을 찾을 수 없습니다.'
            }, status=404)
        
        if not site.latitude or not site.longitude:
            return JsonResponse({
                'success': False,
                'message': '현장의 위치 정보가 설정되지 않았습니다.'
            }, status=400)
        
        # 위치 검증 수행
        verification_result = TimeTrackingAPI.verify_location(
            user_latitude, user_longitude,
            site.latitude, site.longitude,
            tolerance
        )
        
        return JsonResponse({
            'success': True,
            'verification': verification_result,
            'site': {
                'id': str(site.id),
                'name': site.name,
                'latitude': float(site.latitude),
                'longitude': float(site.longitude)
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '잘못된 요청 형식입니다.'
        }, status=400)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'위치 검증 중 오류가 발생했습니다: {str(e)}'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_work_statistics(request):
    """업무 통계 조회"""
    # 쿼리 매개변수
    period = request.GET.get('period', 'week')  # day, week, month, year
    
    now = timezone.now()
    
    # 기간별 필터링
    if period == 'day':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'week':
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == 'year':
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start_date = now - timedelta(days=7)
    
    # 세션 조회
    sessions = WorkSession.objects.filter(
        user=request.user,
        start_time__gte=start_date
    ).select_related('site')
    
    # 통계 계산
    total_sessions = sessions.count()
    total_hours = sum((s.duration_hours for s in sessions), 0)
    completed_sessions = sessions.filter(status='completed').count()
    
    # 현장별 통계
    site_stats = {}
    for session in sessions:
        site_name = session.site.name
        if site_name not in site_stats:
            site_stats[site_name] = {
                'sessions': 0,
                'hours': 0,
                'site_id': str(session.site.id)
            }
        site_stats[site_name]['sessions'] += 1
        site_stats[site_name]['hours'] += session.duration_hours
    
    return JsonResponse({
        'success': True,
        'period': period,
        'statistics': {
            'total_sessions': total_sessions,
            'total_hours': round(total_hours, 2),
            'completed_sessions': completed_sessions,
            'completion_rate': round((completed_sessions / total_sessions * 100) if total_sessions > 0 else 0, 1),
            'average_hours_per_session': round(total_hours / total_sessions, 2) if total_sessions > 0 else 0,
            'site_breakdown': site_stats
        },
        'period_range': {
            'start': start_date.isoformat(),
            'end': now.isoformat()
        }
    })


@login_required
@require_http_methods(["POST"])
def update_session_location(request):
    """세션 위치 정보 업데이트 (실시간 추적)"""
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        accuracy = data.get('accuracy')
        
        if not all([session_id, latitude, longitude]):
            return JsonResponse({
                'success': False,
                'message': '필수 매개변수가 누락되었습니다.'
            }, status=400)
        
        # 세션 확인
        try:
            session = WorkSession.objects.get(
                id=session_id,
                user=request.user,
                status__in=['started', 'paused', 'resumed']
            )
        except WorkSession.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '활성 세션을 찾을 수 없습니다.'
            }, status=404)
        
        # 위치 정보 업데이트 (현재는 마지막 위치만 저장하지만, 필요시 위치 기록 테이블 추가 가능)
        if accuracy and (not session.location_accuracy or accuracy < session.location_accuracy):
            session.location_accuracy = accuracy
        
        # 현장과의 거리 재검증
        if session.site.latitude and session.site.longitude:
            verification_result = TimeTrackingAPI.verify_location(
                latitude, longitude,
                session.site.latitude, session.site.longitude
            )
            
            if verification_result['verified'] and not session.location_verified:
                session.location_verified = True
        
        session.save()
        
        return JsonResponse({
            'success': True,
            'message': '위치 정보가 업데이트되었습니다.',
            'verification': verification_result if 'verification_result' in locals() else None
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'위치 업데이트 중 오류가 발생했습니다: {str(e)}'
        }, status=500)