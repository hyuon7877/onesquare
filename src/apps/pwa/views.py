"""
OneSquare PWA 관련 뷰

오프라인 페이지, 매니페스트 제공, PWA 설치 상태 확인 등
"""

from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.utils import timezone
import json
import mimetypes
import base64
import os


def offline_view(request):
    """오프라인 페이지"""
    return render(request, 'pwa/offline.html', {
        'title': '오프라인 - OneSquare'
    })


@cache_control(max_age=86400)  # 24시간 캐시
def manifest_view(request):
    """Web App Manifest 제공"""
    manifest_path = settings.STATICFILES_DIRS[0] / 'manifest.json'
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)
        
        # 동적으로 아이콘 경로 업데이트 (필요한 경우)
        for icon in manifest_data.get('icons', []):
            if not icon['src'].startswith('http'):
                icon['src'] = request.build_absolute_uri(icon['src'])
        
        return JsonResponse(manifest_data, json_dumps_params={'ensure_ascii': False})
        
    except FileNotFoundError:
        return JsonResponse({'error': 'Manifest not found'}, status=404)


@require_http_methods(["GET"])
def service_worker_view(request):
    """Service Worker 파일 제공"""
    sw_path = settings.STATICFILES_DIRS[0] / 'js' / 'sw.js'
    
    try:
        with open(sw_path, 'r', encoding='utf-8') as f:
            sw_content = f.read()
        
        response = HttpResponse(sw_content, content_type='application/javascript')
        response['Cache-Control'] = 'no-cache'  # Service Worker는 캐시하지 않음
        return response
        
    except FileNotFoundError:
        return HttpResponse('console.error("Service Worker not found");', 
                          content_type='application/javascript', status=404)


@require_http_methods(["GET"])
def pwa_status_api(request):
    """PWA 설치 상태 및 기능 지원 확인 API"""
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    
    # 브라우저별 PWA 지원 확인
    browser_support = {
        'service_worker': True,  # 대부분의 모던 브라우저에서 지원
        'push_notifications': True,
        'background_sync': 'chrome' in user_agent or 'edge' in user_agent,
        'install_prompt': 'chrome' in user_agent or 'edge' in user_agent,
        'standalone_mode': request.META.get('HTTP_X_REQUESTED_WITH') == 'pwa'
    }
    
    return JsonResponse({
        'pwa_supported': True,
        'browser_support': browser_support,
        'manifest_url': request.build_absolute_uri('/manifest.json'),
        'service_worker_url': request.build_absolute_uri('/sw.js'),
        'offline_url': request.build_absolute_uri('/offline/'),
        'features': {
            'offline_support': True,
            'push_notifications': True,
            'background_sync': True,
            'file_sharing': True,
            'shortcuts': True
        }
    })


@require_http_methods(["POST"])
def pwa_install_stats(request):
    """PWA 설치 통계 수집 (선택적)"""
    try:
        data = json.loads(request.body)
        action = data.get('action')  # 'install', 'dismiss', 'uninstall'
        
        # 여기에 설치 통계를 저장하는 로직 추가
        # 예: 데이터베이스에 기록, 분석 도구로 전송 등
        
        return JsonResponse({
            'status': 'success',
            'message': f'PWA {action} recorded'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def browserconfig_view(request):
    """Microsoft 타일 설정"""
    browserconfig_xml = """<?xml version="1.0" encoding="utf-8"?>
<browserconfig>
    <msapplication>
        <tile>
            <square150x150logo src="/static/images/icons/icon-150x150.png"/>
            <TileColor>#2c3e50</TileColor>
        </tile>
    </msapplication>
</browserconfig>"""
    
    return HttpResponse(browserconfig_xml, content_type='application/xml')


@require_http_methods(["POST"])
def share_target_view(request):
    """웹 공유 대상 처리"""
    if request.method == 'POST':
        title = request.POST.get('title', '')
        text = request.POST.get('text', '')
        url = request.POST.get('url', '')
        files = request.FILES.getlist('files')
        
        # 공유된 데이터 처리
        shared_data = {
            'title': title,
            'text': text,
            'url': url,
            'files': [f.name for f in files],
            'timestamp': timezone.now().isoformat()
        }
        
        # 여기에 공유된 데이터를 처리하는 로직 추가
        # 예: 데이터베이스 저장, Notion API 연동 등
        
        # 성공 페이지로 리다이렉트
        return render(request, 'pwa/share_success.html', {
            'shared_data': shared_data
        })
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@require_http_methods(["GET"])  
def pwa_cache_status(request):
    """캐시 상태 확인 API (디버깅용)"""
    if not settings.DEBUG:
        return JsonResponse({'error': 'Only available in debug mode'}, status=403)
    
    # 여기에 캐시 상태를 확인하는 로직을 추가할 수 있음
    # Service Worker에서 제공하는 정보를 기반으로
    
    return JsonResponse({
        'debug_mode': True,
        'cache_info': 'Available in browser DevTools > Application > Storage',
        'service_worker_status': 'Check browser DevTools > Application > Service Workers'
    })


@require_http_methods(["GET"])
def vapid_public_key_view(request):
    """VAPID 공개키 제공"""
    # 개발용 기본 VAPID 키 (실제 운영에서는 환경변수에서 로드)
    public_key = getattr(settings, 'VAPID_PUBLIC_KEY', 
                        'BEl62iUYgUivxIkv69yViEuiBIa40HI80NqIUHngOiZhgUq-dS-bWlzlVYfVjkCDKuP14k6RVEiPUY-BqBjPFSY')
    
    return JsonResponse({
        'publicKey': public_key,
        'supported': True
    })


@require_http_methods(["POST"])
@csrf_exempt  # 개발용, 실제로는 CSRF 토큰 사용 권장
def push_subscribe_view(request):
    """푸시 알림 구독 처리"""
    try:
        data = json.loads(request.body)
        subscription = data.get('subscription')
        
        if not subscription:
            return JsonResponse({'error': 'No subscription data provided'}, status=400)
        
        # 구독 정보 저장 (실제로는 데이터베이스에 저장)
        # 여기서는 로그만 출력
        print(f"Push subscription received: {subscription.get('endpoint', 'Unknown')}")
        
        # Notion API를 통해 구독 정보 저장 (선택사항)
        # save_subscription_to_notion(subscription, request.user if request.user.is_authenticated else None)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Push notification subscription successful',
            'subscription_id': subscription.get('endpoint', '')[-10:]  # 마지막 10자리를 ID로 사용
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def push_unsubscribe_view(request):
    """푸시 알림 구독 해제"""
    try:
        data = json.loads(request.body)
        endpoint = data.get('endpoint')
        
        if not endpoint:
            return JsonResponse({'error': 'No endpoint provided'}, status=400)
        
        # 구독 해제 처리 (실제로는 데이터베이스에서 제거)
        print(f"Push unsubscribe: {endpoint}")
        
        return JsonResponse({
            'status': 'success',
            'message': 'Push notification unsubscribed successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def push_test_view(request):
    """테스트 푸시 알림 전송"""
    try:
        data = json.loads(request.body)
        title = data.get('title', 'OneSquare 테스트')
        message = data.get('message', '테스트 알림입니다.')
        url = data.get('url', '/')
        
        # 실제 푸시 알림 전송은 백그라운드 작업으로 처리
        # send_push_notification(title, message, url)
        
        # 개발 단계에서는 성공 응답만 반환
        print(f"Test push notification: {title} - {message}")
        
        return JsonResponse({
            'status': 'success',
            'message': 'Test push notification sent',
            'data': {
                'title': title,
                'body': message,
                'url': url
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET", "POST"])
def push_settings_view(request):
    """푸시 알림 설정 관리"""
    if request.method == 'GET':
        # 기본 설정 반환 (실제로는 사용자별 설정 조회)
        default_settings = {
            'enabled': True,
            'types': {
                'notion_sync': True,
                'task_updates': True,
                'system_updates': False,
                'offline_sync': True
            },
            'quiet_hours': {
                'enabled': False,
                'start': '22:00',
                'end': '08:00',
                'timezone': 'Asia/Seoul'
            },
            'sound': {
                'enabled': True,
                'volume': 0.8
            },
            'vibration': {
                'enabled': True,
                'pattern': [100, 50, 100]
            }
        }
        
        return JsonResponse(default_settings)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # 설정 검증 및 저장 (실제로는 데이터베이스 또는 Notion에 저장)
            print(f"Push settings updated: {data}")
            
            return JsonResponse({
                'status': 'success',
                'message': 'Push notification settings updated',
                'settings': data
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def push_stats_view(request):
    """푸시 알림 통계"""
    # 실제로는 데이터베이스에서 통계 조회
    stats = {
        'total_sent': 0,
        'total_delivered': 0,
        'total_clicked': 0,
        'last_7_days': {
            'sent': 0,
            'delivered': 0,
            'clicked': 0
        },
        'by_type': {
            'notion_sync': {'sent': 0, 'clicked': 0},
            'task_updates': {'sent': 0, 'clicked': 0},
            'system_updates': {'sent': 0, 'clicked': 0}
        },
        'last_notification': None
    }
    
    return JsonResponse(stats)


# 푸시 알림 전송 헬퍼 함수 (백그라운드 작업용)
def send_push_notification(title, message, url=None, user_ids=None):
    """
    실제 푸시 알림 전송 함수
    백그라운드 작업(Celery 등)으로 실행하는 것을 권장
    """
    try:
        # 여기에 실제 푸시 알림 전송 로직 구현
        # 예: Web Push Protocol 사용
        
        print(f"Sending push notification: {title} - {message}")
        
        # 구독자 목록 조회 및 알림 전송
        # for subscription in get_active_subscriptions(user_ids):
        #     send_to_subscription(subscription, title, message, url)
        
        return True
        
    except Exception as e:
        print(f"Failed to send push notification: {e}")
        return False


def save_subscription_to_notion(subscription, user=None):
    """
    Notion에 푸시 구독 정보 저장 (선택사항)
    """
    try:
        # Notion API를 사용하여 구독 정보 저장
        subscription_data = {
            'endpoint': subscription.get('endpoint'),
            'keys': subscription.get('keys', {}),
            'user_id': user.id if user else None,
            'created_at': timezone.now().isoformat(),
            'user_agent': subscription.get('user_agent', ''),
            'timezone': subscription.get('timezone', 'UTC')
        }
        
        print(f"Saving subscription to Notion: {subscription_data}")
        return True
        
    except Exception as e:
        print(f"Failed to save subscription to Notion: {e}")
        return False