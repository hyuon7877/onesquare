"""
OneSquare 매출 관리 - Notion 동기화 API 뷰
실시간 동기화 및 상태 관리 API
"""

import asyncio
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils.decorators import method_decorator
from django.views.generic import View
import json

from .notion_sync import NotionRevenueSync
from .permissions import RevenuePermissionManager, UserRole, require_revenue_permission

logger = logging.getLogger(__name__)

class NotionSyncStatusView(View):
    """Notion 동기화 상태 조회"""
    
    @method_decorator(login_required)
    def get(self, request):
        sync_service = NotionRevenueSync()
        sync_status = sync_service.get_sync_status()
        
        # 사용자 권한 정보 추가
        user_role = RevenuePermissionManager.get_user_role(request.user)
        can_sync = user_role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]
        
        return JsonResponse({
            'sync_status': sync_status,
            'user_permissions': {
                'can_sync': can_sync,
                'can_view_status': True,
                'user_role': user_role
            }
        })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_revenue_permission('write')
def trigger_full_sync(request):
    """전체 데이터 동기화 트리거 (관리자만)"""
    user_role = RevenuePermissionManager.get_user_role(request.user)
    
    if user_role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        return Response(
            {'error': '전체 동기화 권한이 없습니다.'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        sync_service = NotionRevenueSync()
        
        if not sync_service.is_sync_available():
            return Response(
                {'error': 'Notion API 설정이 필요합니다.'}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        # 비동기 동기화 실행
        async def run_sync():
            return await sync_service.sync_all_revenue_data(request.user)
        
        # 이벤트 루프에서 실행
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        sync_result = loop.run_until_complete(run_sync())
        
        if sync_result['success']:
            return Response(sync_result, status=status.HTTP_200_OK)
        else:
            return Response(sync_result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"전체 동기화 트리거 실패: {e}")
        return Response(
            {'error': f'동기화 실행 중 오류: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated]) 
@require_revenue_permission('write')
def sync_single_revenue(request, revenue_id):
    """단일 매출 데이터 동기화"""
    user_role = RevenuePermissionManager.get_user_role(request.user)
    
    if user_role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        return Response(
            {'error': '개별 동기화 권한이 없습니다.'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        direction = request.data.get('direction', 'both')
        if direction not in ['django_to_notion', 'notion_to_django', 'both']:
            return Response(
                {'error': '유효하지 않은 동기화 방향입니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        sync_service = NotionRevenueSync()
        
        if not sync_service.is_sync_available():
            return Response(
                {'error': 'Notion API 설정이 필요합니다.'}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        # 비동기 동기화 실행
        async def run_single_sync():
            return await sync_service.sync_single_revenue(revenue_id, direction)
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        sync_result = loop.run_until_complete(run_single_sync())
        
        if sync_result['success']:
            return Response(sync_result, status=status.HTTP_200_OK)
        else:
            return Response(sync_result, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"개별 동기화 실패 ({revenue_id}): {e}")
        return Response(
            {'error': f'개별 동기화 실행 중 오류: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@require_http_methods(["POST"])
def notion_webhook(request):
    """Notion 웹훅 수신 엔드포인트 (실시간 동기화)"""
    try:
        # 웹훅 데이터 파싱
        webhook_data = json.loads(request.body)
        
        # 보안: 웹훅 시그니처 검증 (실제 구현에서는 Notion 시크릿 키로 검증)
        # webhook_signature = request.headers.get('X-Notion-Signature')
        # if not verify_webhook_signature(request.body, webhook_signature):
        #     return JsonResponse({'error': 'Invalid signature'}, status=401)
        
        event_type = webhook_data.get('type')
        page_data = webhook_data.get('data', {})
        
        logger.info(f"Notion 웹훅 수신: {event_type}")
        
        # 페이지 업데이트 이벤트 처리
        if event_type in ['page.updated', 'page.created', 'page.deleted']:
            page_id = page_data.get('id')
            
            if page_id:
                # 백그라운드에서 동기화 처리 (실제로는 Celery 등 사용)
                process_notion_page_update(page_id, event_type)
        
        return JsonResponse({'status': 'success'}, status=200)
        
    except json.JSONDecodeError:
        logger.error("잘못된 JSON 형식의 웹훅 데이터")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"웹훅 처리 실패: {e}")
        return JsonResponse({'error': 'Webhook processing failed'}, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_revenue_permission('write')
def clear_sync_cache(request):
    """동기화 캐시 초기화 (디버깅용)"""
    user_role = RevenuePermissionManager.get_user_role(request.user)
    
    if user_role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        return Response(
            {'error': '캐시 초기화 권한이 없습니다.'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        sync_service = NotionRevenueSync()
        sync_service.clear_sync_cache()
        
        return Response(
            {'message': '동기화 캐시가 초기화되었습니다.'}, 
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"캐시 초기화 실패: {e}")
        return Response(
            {'error': f'캐시 초기화 중 오류: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sync_history(request):
    """동기화 히스토리 조회"""
    user_role = RevenuePermissionManager.get_user_role(request.user)
    
    if user_role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MIDDLE_MANAGER]:
        return Response(
            {'error': '동기화 히스토리 조회 권한이 없습니다.'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        # 동기화 히스토리 데이터 조회 (실제로는 별도 모델에 저장)
        from .models import RevenueRecord
        
        # Notion과 연결된 매출 기록들
        synced_records = RevenueRecord.objects.exclude(
            notion_page_id__isnull=True
        ).exclude(
            notion_page_id__exact=''
        ).order_by('-last_synced_at')[:50]
        
        history_data = []
        for record in synced_records:
            history_data.append({
                'id': str(record.id),
                'project_name': record.project.name,
                'client_name': record.client.name,
                'amount': float(record.amount),
                'notion_page_id': record.notion_page_id,
                'last_synced_at': record.last_synced_at.isoformat() if record.last_synced_at else None,
                'created_at': record.created_at.isoformat(),
                'updated_at': record.updated_at.isoformat()
            })
        
        return Response({
            'synced_records': history_data,
            'total_synced': len(history_data),
            'user_role': user_role
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"동기화 히스토리 조회 실패: {e}")
        return Response(
            {'error': f'히스토리 조회 중 오류: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notion_config_check(request):
    """Notion API 설정 상태 확인"""
    user_role = RevenuePermissionManager.get_user_role(request.user)
    
    if user_role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        return Response(
            {'error': 'Notion 설정 조회 권한이 없습니다.'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        from django.conf import settings
        
        notion_token = getattr(settings, 'NOTION_TOKEN', None)
        database_id = getattr(settings, 'NOTION_REVENUE_DATABASE_ID', None)
        
        config_status = {
            'notion_token_configured': bool(notion_token),
            'database_id_configured': bool(database_id),
            'database_id_preview': database_id[:8] + '...' if database_id else None,
            'is_ready': bool(notion_token and database_id)
        }
        
        # Notion API 연결 테스트
        if config_status['is_ready']:
            sync_service = NotionRevenueSync()
            try:
                if sync_service.notion_client:
                    # 간단한 API 호출로 연결 테스트
                    test_result = sync_service.notion_client.databases.retrieve(database_id)
                    config_status['connection_test'] = 'success'
                    config_status['database_title'] = test_result.get('title', [{}])[0].get('text', {}).get('content', 'Unknown')
                else:
                    config_status['connection_test'] = 'failed'
            except Exception as e:
                config_status['connection_test'] = f'failed: {str(e)}'
        
        return Response(config_status, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Notion 설정 확인 실패: {e}")
        return Response(
            {'error': f'설정 확인 중 오류: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# 백그라운드 처리 함수들
def process_notion_page_update(page_id: str, event_type: str):
    """Notion 페이지 업데이트 백그라운드 처리"""
    try:
        logger.info(f"Notion 페이지 업데이트 처리 시작: {page_id} ({event_type})")
        
        # 실제로는 Celery 태스크로 처리
        # from .tasks import sync_notion_page_update
        # sync_notion_page_update.delay(page_id, event_type)
        
        # 임시로 동기 처리
        sync_service = NotionRevenueSync()
        
        if event_type in ['page.updated', 'page.created']:
            # 해당 페이지의 Django 레코드 찾기 및 동기화
            from .models import RevenueRecord
            
            try:
                revenue = RevenueRecord.objects.get(notion_page_id=page_id)
                
                # 비동기 동기화 실행
                async def run_page_sync():
                    return await sync_service.sync_single_revenue(
                        str(revenue.id), 
                        'notion_to_django'
                    )
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(run_page_sync())
                
                logger.info(f"페이지 동기화 완료: {page_id} -> {result}")
                
            except RevenueRecord.DoesNotExist:
                logger.warning(f"Notion 페이지에 대응하는 Django 레코드 없음: {page_id}")
                
        elif event_type == 'page.deleted':
            # 페이지 삭제 시 Django 레코드도 처리 (선택적)
            # 실제로는 소프트 삭제나 아카이브 처리를 권장
            logger.info(f"Notion 페이지 삭제됨: {page_id}")
        
    except Exception as e:
        logger.error(f"Notion 페이지 업데이트 처리 실패: {e}")

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """웹훅 서명 검증 (보안)"""
    # 실제 구현에서는 Notion에서 제공하는 시크릿 키로 HMAC 서명 검증
    # import hmac
    # import hashlib
    # from django.conf import settings
    # 
    # secret = settings.NOTION_WEBHOOK_SECRET
    # expected_signature = hmac.new(
    #     secret.encode('utf-8'),
    #     payload,
    #     hashlib.sha256
    # ).hexdigest()
    # 
    # return hmac.compare_digest(signature, expected_signature)
    
    # 임시로 항상 True 반환 (개발 환경)
    return True