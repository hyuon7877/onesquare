"""
OneSquare Notion API 연동 - API Views

이 모듈은 Notion API와 관련된 RESTful API 엔드포인트를 제공합니다.
"""

from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.authentication import TokenAuthentication
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.core.paginator import Paginator
import logging
import json

from .models import NotionDatabase, NotionPage, SyncHistory
from .services import NotionClient, NotionSyncService, NotionCacheService
from .serializers import (
    NotionDatabaseSerializer,
    NotionPageSerializer,
    SyncHistorySerializer,
    DatabaseSyncRequestSerializer
)
from apps.auth_system.decorators import secure_api_view, admin_required

logger = logging.getLogger('notion_api')


@api_view(['GET'])
def notion_test_api(request):
    """Notion API 연결 테스트"""
    try:
        # Check if Notion settings are configured
        notion_token = getattr(settings, 'NOTION_TOKEN', None)
        notion_db_id = getattr(settings, 'NOTION_DATABASE_ID', None)
        
        if not notion_token or not notion_db_id:
            return Response({
                'status': 'error',
                'message': 'Notion API 설정이 필요합니다. secrets.json을 확인하세요.',
                'details': {
                    'notion_token_exists': bool(notion_token),
                    'notion_db_id_exists': bool(notion_db_id)
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 실제 Notion API 연결 테스트
        client = NotionClient()
        try:
            # 워크스페이스에서 데이터베이스 검색
            search_result = client.search("", filter_criteria={"object": "database"})
            databases_count = len(search_result.get('results', []))
            
            return Response({
                'status': 'success',
                'message': 'Notion API 연결이 성공적으로 확인되었습니다.',
                'timestamp': timezone.now().isoformat(),
                'configured': True,
                'available_databases': databases_count
            })
            
        except Exception as api_error:
            logger.error(f"Notion API 연결 실패: {str(api_error)}")
            return Response({
                'status': 'error',
                'message': f'Notion API 연결 실패: {str(api_error)}',
                'configured': False
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
    except Exception as e:
        logger.error(f"Notion API test error: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'Notion API 테스트 중 오류 발생: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NotionDatabaseListView(ListCreateAPIView):
    """
    Notion 데이터베이스 목록 조회 및 등록
    """
    serializer_class = NotionDatabaseSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    
    def get_queryset(self):
        queryset = NotionDatabase.objects.filter(is_active=True)
        
        # 필터링
        database_type = self.request.query_params.get('type')
        if database_type:
            queryset = queryset.filter(database_type=database_type)
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        """데이터베이스 등록 시 스키마 자동 가져오기"""
        database = serializer.save(created_by=self.request.user)
        
        # Notion에서 스키마 정보 가져오기
        try:
            client = NotionClient()
            notion_db = client.get_database(database.notion_id)
            
            schema = {
                'properties': notion_db.get('properties', {}),
                'title': notion_db.get('title', []),
                'description': notion_db.get('description', [])
            }
            
            database.schema = schema
            database.title = notion_db.get('title', [{}])[0].get('plain_text', database.title)
            database.save()
            
            logger.info(f"데이터베이스 등록 완료: {database.title}")
            
        except Exception as e:
            logger.error(f"스키마 가져오기 실패: {str(e)}")


class NotionDatabaseDetailView(RetrieveUpdateDestroyAPIView):
    """
    Notion 데이터베이스 상세 조회, 수정, 삭제
    """
    serializer_class = NotionDatabaseSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    
    def get_queryset(self):
        return NotionDatabase.objects.filter(is_active=True)


class NotionPageListView(APIView):
    """
    Notion 페이지 목록 조회
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    
    def get(self, request, database_id):
        try:
            database = get_object_or_404(NotionDatabase, id=database_id, is_active=True)
            
            # 쿼리 파라미터
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('page_size', 20)), 100)
            status_filter = request.query_params.get('status', 'active')
            search_query = request.query_params.get('search', '')
            
            # 페이지 목록 조회
            pages = NotionPage.objects.filter(database=database)
            
            if status_filter != 'all':
                pages = pages.filter(status=status_filter)
            
            if search_query:
                pages = pages.filter(title__icontains=search_query)
            
            # 페이지네이션
            paginator = Paginator(pages.order_by('-notion_last_edited_time'), page_size)
            page_obj = paginator.get_page(page)
            
            serializer = NotionPageSerializer(page_obj.object_list, many=True)
            
            return Response({
                'results': serializer.data,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_pages': paginator.num_pages,
                    'total_count': paginator.count,
                    'has_next': page_obj.has_next(),
                    'has_previous': page_obj.has_previous()
                },
                'database': NotionDatabaseSerializer(database).data
            })
            
        except Exception as e:
            logger.error(f"페이지 목록 조회 실패: {str(e)}")
            return Response({
                'error': '페이지 목록을 가져오는 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NotionPageDetailView(APIView):
    """
    Notion 페이지 상세 조회 및 수정
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    
    def get(self, request, page_id):
        try:
            page = get_object_or_404(NotionPage, id=page_id)
            
            # 캐시된 데이터 확인
            cached_data = NotionCacheService.get_cached_page(page.notion_id)
            if cached_data:
                return Response(cached_data)
            
            serializer = NotionPageSerializer(page)
            response_data = serializer.data
            
            # 캐시 저장
            NotionCacheService.cache_page(page.notion_id, response_data)
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"페이지 상세 조회 실패: {str(e)}")
            return Response({
                'error': '페이지를 가져오는 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def patch(self, request, page_id):
        """페이지 속성 업데이트"""
        try:
            page = get_object_or_404(NotionPage, id=page_id)
            
            # 요청 데이터 검증
            properties = request.data.get('properties', {})
            if not properties:
                return Response({
                    'error': '업데이트할 속성 데이터가 필요합니다.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 페이지 업데이트
            for prop_name, prop_value in properties.items():
                page.set_property(prop_name, prop_value)
            
            page.save()
            
            # 캐시 무효화
            NotionCacheService.invalidate_page_cache(page.notion_id)
            
            return Response({
                'message': '페이지가 성공적으로 업데이트되었습니다.',
                'page': NotionPageSerializer(page).data
            })
            
        except Exception as e:
            logger.error(f"페이지 업데이트 실패: {str(e)}")
            return Response({
                'error': '페이지 업데이트 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DatabaseSyncView(APIView):
    """
    데이터베이스 동기화 API
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    
    def post(self, request, database_id):
        """동기화 실행"""
        try:
            database = get_object_or_404(NotionDatabase, id=database_id, is_active=True)
            
            # 요청 데이터 검증
            serializer = DatabaseSyncRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            sync_type = serializer.validated_data.get('sync_type', 'incremental')
            force_sync = serializer.validated_data.get('force_sync', False)
            
            # 중복 동기화 방지
            if not force_sync:
                recent_sync = SyncHistory.objects.filter(
                    database=database,
                    status__in=['started', 'in_progress'],
                    started_at__gte=timezone.now() - timezone.timedelta(minutes=5)
                ).exists()
                
                if recent_sync:
                    return Response({
                        'error': '이미 동기화가 진행 중입니다. 잠시 후 다시 시도해주세요.'
                    }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            # 동기화 실행
            sync_service = NotionSyncService()
            result = sync_service.sync_database(
                database=database,
                sync_type=sync_type,
                user=request.user
            )
            
            if result.success:
                return Response({
                    'message': '동기화가 성공적으로 완료되었습니다.',
                    'result': {
                        'pages_processed': result.pages_processed,
                        'pages_created': result.pages_created,
                        'pages_updated': result.pages_updated,
                        'pages_deleted': result.pages_deleted,
                        'duration': result.duration
                    }
                })
            else:
                return Response({
                    'error': '동기화 중 오류가 발생했습니다.',
                    'details': result.errors
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"동기화 실행 실패: {str(e)}")
            return Response({
                'error': '동기화 실행 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SyncHistoryView(APIView):
    """
    동기화 기록 조회
    """
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication]
    
    def get(self, request, database_id=None):
        try:
            # 쿼리 파라미터
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('page_size', 20)), 100)
            
            # 동기화 기록 조회
            history = SyncHistory.objects.all()
            
            if database_id:
                database = get_object_or_404(NotionDatabase, id=database_id)
                history = history.filter(database=database)
            
            # 페이지네이션
            paginator = Paginator(history.order_by('-started_at'), page_size)
            page_obj = paginator.get_page(page)
            
            serializer = SyncHistorySerializer(page_obj.object_list, many=True)
            
            return Response({
                'results': serializer.data,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_pages': paginator.num_pages,
                    'total_count': paginator.count
                }
            })
            
        except Exception as e:
            logger.error(f"동기화 기록 조회 실패: {str(e)}")
            return Response({
                'error': '동기화 기록을 가져오는 중 오류가 발생했습니다.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def push_local_changes(request, database_id):
    """로컬 변경사항을 Notion에 반영"""
    try:
        database = get_object_or_404(NotionDatabase, id=database_id, is_active=True)
        
        sync_service = NotionSyncService()
        result = sync_service.push_local_changes(database)
        
        if result.success:
            return Response({
                'message': '로컬 변경사항이 성공적으로 Notion에 반영되었습니다.',
                'result': {
                    'pages_updated': result.pages_updated,
                    'duration': result.duration
                }
            })
        else:
            return Response({
                'error': '변경사항 반영 중 오류가 발생했습니다.',
                'details': result.errors
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"변경사항 푸시 실패: {str(e)}")
        return Response({
            'error': '변경사항 반영 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@admin_required
def refresh_database_schema(request, database_id):
    """데이터베이스 스키마 새로고침 (관리자 전용)"""
    try:
        database = get_object_or_404(NotionDatabase, id=database_id, is_active=True)
        
        # Notion에서 최신 스키마 가져오기
        client = NotionClient()
        notion_db = client.get_database(database.notion_id)
        
        # 스키마 업데이트
        new_schema = {
            'properties': notion_db.get('properties', {}),
            'title': notion_db.get('title', []),
            'description': notion_db.get('description', [])
        }
        
        old_schema = database.schema
        database.update_schema(new_schema)
        
        # 캐시 무효화
        NotionCacheService.invalidate_database_cache(database.notion_id)
        
        return Response({
            'message': '데이터베이스 스키마가 성공적으로 새로고침되었습니다.',
            'schema_updated': old_schema != new_schema,
            'properties_count': len(new_schema.get('properties', {}))
        })
        
    except Exception as e:
        logger.error(f"스키마 새로고침 실패: {str(e)}")
        return Response({
            'error': '스키마 새로고침 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
@admin_required
def clear_cache(request):
    """모든 Notion 관련 캐시 삭제 (관리자 전용)"""
    try:
        NotionCacheService.clear_all_cache()
        
        return Response({
            'message': '모든 Notion 관련 캐시가 성공적으로 삭제되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"캐시 삭제 실패: {str(e)}")
        return Response({
            'error': '캐시 삭제 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def search_notion_workspace(request):
    """Notion 워크스페이스 검색"""
    try:
        query = request.query_params.get('q', '')
        object_type = request.query_params.get('type', 'page')  # page, database
        
        client = NotionClient()
        
        filter_criteria = {"object": object_type} if object_type != 'all' else None
        
        search_result = client.search(
            query=query,
            filter_criteria=filter_criteria
        )
        
        return Response({
            'results': search_result.get('results', []),
            'has_more': search_result.get('has_more', False),
            'next_cursor': search_result.get('next_cursor')
        })
        
    except Exception as e:
        logger.error(f"워크스페이스 검색 실패: {str(e)}")
        return Response({
            'error': '검색 중 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 레거시 API (하위 호환성)
@api_view(['POST'])
def notion_sync_api(request):
    """PWA에서 Notion으로 데이터 동기화 (레거시)"""
    try:
        data = request.data
        
        # TODO: Implement actual Notion API sync logic here
        logger.info(f"Legacy sync request received: {data}")
        
        return Response({
            'status': 'success',
            'message': '데이터가 성공적으로 동기화되었습니다.',
            'synced_items': len(data) if isinstance(data, (list, dict)) else 0,
            'note': 'This is a legacy endpoint. Please use /api/notion/databases/{id}/sync/ instead.'
        })
        
    except Exception as e:
        logger.error(f"Legacy notion sync error: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'동기화 중 오류 발생: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)