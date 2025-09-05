"""
OneSquare Notion API 연동 - 서비스 클래스

이 모듈은 Notion API와의 통신을 담당하는 서비스 클래스들을 정의합니다.
- NotionClient: Notion API 클라이언트
- NotionSyncService: 데이터 동기화 서비스
- NotionCacheService: 캐시 관리 서비스
"""

import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from notion_client import Client
from notion_client.errors import APIResponseError, RequestTimeoutError

from .models import NotionDatabase, NotionPage, SyncHistory
from .exceptions import (
    NotionAPIError, NotionRateLimitError, NotionServerError,
    NotionNetworkError, NotionTimeoutError, NotionSyncError,
    get_exception_from_response
)
from .retry_utils import with_retry, DEFAULT_RETRY_CONFIG, notion_circuit_breaker

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """동기화 결과"""
    success: bool
    sync_id: str
    total_pages: int
    pages_created: int
    pages_updated: int
    pages_deleted: int
    pages_failed: int
    errors: List[str]
    error: Optional[str]
    duration: float
    
    @property
    def success_rate(self) -> float:
        """성공률 계산"""
        if self.total_pages == 0:
            return 100.0
        return ((self.total_pages - self.pages_failed) / self.total_pages) * 100


class NotionClient:
    """
    Notion API 클라이언트
    
    Notion API와의 모든 통신을 처리합니다.
    """
    
    def __init__(self):
        self.client = Client(auth=settings.NOTION_TOKEN)
        self.api_version = "2022-06-28"
        self.rate_limit_delay = getattr(settings, 'NOTION_RATE_LIMIT_DELAY', 0.1)
    
    def _handle_api_error(self, error: APIResponseError, operation: str) -> NotionAPIError:
        """API 오류를 적절한 커스텀 예외로 변환"""
        try:
            # APIResponseError를 적절한 커스텀 예외로 변환
            if hasattr(error, 'response'):
                return get_exception_from_response(error.response)
            else:
                # 기본 처리
                return NotionAPIError(f"{operation} 실패: {str(error)}")
        except Exception:
            return NotionAPIError(f"{operation} 실패: {str(error)}")
    
    def _handle_timeout_error(self, error: RequestTimeoutError, operation: str) -> NotionTimeoutError:
        """타임아웃 오류 처리"""
        return NotionTimeoutError(f"{operation} 타임아웃: {str(error)}")
    
    def _handle_network_error(self, error: Exception, operation: str) -> NotionNetworkError:
        """네트워크 오류 처리"""
        return NotionNetworkError(f"{operation} 네트워크 오류: {str(error)}")
    
    @notion_circuit_breaker
    @with_retry(DEFAULT_RETRY_CONFIG)
    def get_database(self, database_id: str) -> Dict:
        """데이터베이스 메타데이터 조회"""
        try:
            response = self.client.databases.retrieve(database_id=database_id)
            logger.info(f"데이터베이스 조회 성공: {database_id}")
            return response
        except APIResponseError as e:
            logger.error(f"데이터베이스 조회 실패 {database_id}: {e}")
            raise self._handle_api_error(e, "데이터베이스 조회")
        except RequestTimeoutError as e:
            logger.error(f"데이터베이스 조회 타임아웃 {database_id}: {e}")
            raise self._handle_timeout_error(e, "데이터베이스 조회")
        except Exception as e:
            logger.error(f"데이터베이스 조회 네트워크 오류 {database_id}: {e}")
            raise self._handle_network_error(e, "데이터베이스 조회")
    
    @notion_circuit_breaker
    @with_retry(DEFAULT_RETRY_CONFIG)
    def query_database(self, database_id: str, filter_criteria: Optional[Dict] = None, 
                      sorts: Optional[List] = None, start_cursor: Optional[str] = None, 
                      page_size: int = 100) -> Dict:
        """데이터베이스 쿼리"""
        try:
            query_params = {
                "database_id": database_id,
                "page_size": page_size
            }
            
            if filter_criteria:
                query_params["filter"] = filter_criteria
            
            if sorts:
                query_params["sorts"] = sorts
            
            if start_cursor:
                query_params["start_cursor"] = start_cursor
            
            response = self.client.databases.query(**query_params)
            logger.info(f"데이터베이스 쿼리 성공: {database_id}, 결과: {len(response['results'])}개")
            return response
            
        except APIResponseError as e:
            logger.error(f"데이터베이스 쿼리 실패 {database_id}: {e}")
            raise self._handle_api_error(e, "데이터베이스 쿼리")
        except RequestTimeoutError as e:
            logger.error(f"데이터베이스 쿼리 타임아웃 {database_id}: {e}")
            raise self._handle_timeout_error(e, "데이터베이스 쿼리")
        except Exception as e:
            logger.error(f"데이터베이스 쿼리 네트워크 오류 {database_id}: {e}")
            raise self._handle_network_error(e, "데이터베이스 쿼리")
    
    @notion_circuit_breaker
    @with_retry(DEFAULT_RETRY_CONFIG)
    def get_page(self, page_id: str) -> Dict:
        """페이지 조회"""
        try:
            response = self.client.pages.retrieve(page_id=page_id)
            logger.debug(f"페이지 조회 성공: {page_id}")
            return response
        except APIResponseError as e:
            logger.error(f"페이지 조회 실패 {page_id}: {e}")
            raise self._handle_api_error(e, "페이지 조회")
        except RequestTimeoutError as e:
            logger.error(f"페이지 조회 타임아웃 {page_id}: {e}")
            raise self._handle_timeout_error(e, "페이지 조회")
        except Exception as e:
            logger.error(f"페이지 조회 네트워크 오류 {page_id}: {e}")
            raise self._handle_network_error(e, "페이지 조회")
    
    def get_page_content(self, page_id: str) -> List[Dict]:
        """페이지 내용 블록 조회"""
        try:
            response = self.client.blocks.children.list(block_id=page_id)
            logger.debug(f"페이지 내용 조회 성공: {page_id}")
            return response.get('results', [])
        except APIResponseError as e:
            logger.error(f"페이지 내용 조회 실패 {page_id}: {e}")
            raise
    
    @notion_circuit_breaker
    @with_retry(DEFAULT_RETRY_CONFIG)
    def create_page(self, database_id: str, properties: Dict, 
                   content_blocks: Optional[List] = None) -> Dict:
        """페이지 생성"""
        try:
            page_data = {
                "parent": {"database_id": database_id},
                "properties": properties
            }
            
            if content_blocks:
                page_data["children"] = content_blocks
            
            response = self.client.pages.create(**page_data)
            logger.info(f"페이지 생성 성공: {response['id']}")
            return response
        except APIResponseError as e:
            logger.error(f"페이지 생성 실패 {database_id}: {e}")
            raise self._handle_api_error(e, "페이지 생성")
        except RequestTimeoutError as e:
            logger.error(f"페이지 생성 타임아웃 {database_id}: {e}")
            raise self._handle_timeout_error(e, "페이지 생성")
        except Exception as e:
            logger.error(f"페이지 생성 네트워크 오류 {database_id}: {e}")
            raise self._handle_network_error(e, "페이지 생성")
    
    def update_page(self, page_id: str, properties: Dict) -> Dict:
        """페이지 업데이트"""
        try:
            response = self.client.pages.update(
                page_id=page_id,
                properties=properties
            )
            logger.info(f"페이지 업데이트 성공: {page_id}")
            return response
        except APIResponseError as e:
            logger.error(f"페이지 업데이트 실패 {page_id}: {e}")
            raise
    
    def archive_page(self, page_id: str) -> Dict:
        """페이지 보관 (삭제)"""
        try:
            response = self.client.pages.update(
                page_id=page_id,
                archived=True
            )
            logger.info(f"페이지 보관 성공: {page_id}")
            return response
        except APIResponseError as e:
            logger.error(f"페이지 보관 실패 {page_id}: {e}")
            raise
    
    def search(self, query: str, filter_criteria: Optional[Dict] = None, 
              sorts: Optional[List] = None, start_cursor: Optional[str] = None, 
              page_size: int = 100) -> Dict:
        """전체 워크스페이스 검색"""
        try:
            search_params = {
                "query": query,
                "page_size": page_size
            }
            
            if filter_criteria:
                search_params["filter"] = filter_criteria
            
            if sorts:
                search_params["sorts"] = sorts
            
            if start_cursor:
                search_params["start_cursor"] = start_cursor
            
            response = self.client.search(**search_params)
            logger.info(f"검색 성공: '{query}', 결과: {len(response['results'])}개")
            return response
        except APIResponseError as e:
            logger.error(f"검색 실패 '{query}': {e}")
            raise


class NotionSyncService:
    """
    Notion 동기화 서비스
    
    Notion과 로컬 데이터베이스 간의 데이터 동기화를 관리합니다.
    """
    
    def __init__(self):
        self.client = NotionClient()
    
    def sync_database(self, database: NotionDatabase, sync_type: str = 'incremental', 
                     user=None) -> SyncResult:
        """데이터베이스 동기화"""
        start_time = timezone.now()
        
        # 동기화 히스토리 생성
        sync_history = SyncHistory.objects.create(
            database=database,
            sync_type=sync_type,
            triggered_by=user
        )
        
        try:
            logger.info(f"동기화 시작: {database.title} ({sync_type})")
            
            # 1. 데이터베이스 스키마 업데이트
            self._update_database_schema(database)
            
            # 2. 페이지 데이터 동기화
            if sync_type == 'full_sync':
                result = self._full_sync(database, sync_history)
            else:
                result = self._incremental_sync(database, sync_history)
            
            # 3. 동기화 완료 처리
            database.last_synced = timezone.now()
            database.save(update_fields=['last_synced'])
            
            # 히스토리 업데이트
            sync_history.total_pages = result.pages_processed
            sync_history.pages_created = result.pages_created
            sync_history.pages_updated = result.pages_updated
            sync_history.pages_deleted = result.pages_deleted
            sync_history.mark_completed()
            
            logger.info(f"동기화 완료: {database.title}, 처리: {result.pages_processed}개")
            return result
            
        except Exception as e:
            logger.error(f"동기화 실패: {database.title} - {str(e)}")
            sync_history.mark_failed(str(e))
            
            return SyncResult(
                success=False,
                pages_processed=0,
                pages_created=0,
                pages_updated=0,
                pages_deleted=0,
                errors=[str(e)],
                duration=(timezone.now() - start_time).total_seconds()
            )
    
    def _update_database_schema(self, database: NotionDatabase):
        """데이터베이스 스키마 업데이트"""
        try:
            notion_db = self.client.get_database(database.notion_id)
            
            # 스키마 변경사항 확인
            new_schema = {
                'properties': notion_db.get('properties', {}),
                'title': notion_db.get('title', []),
                'description': notion_db.get('description', [])
            }
            
            if database.schema != new_schema:
                database.update_schema(new_schema)
                logger.info(f"데이터베이스 스키마 업데이트: {database.title}")
                
        except Exception as e:
            logger.warning(f"스키마 업데이트 실패: {database.title} - {str(e)}")
    
    def _full_sync(self, database: NotionDatabase, sync_history: SyncHistory) -> SyncResult:
        """전체 동기화"""
        start_time = timezone.now()
        pages_processed = 0
        pages_created = 0
        pages_updated = 0
        pages_deleted = 0
        errors = []
        
        try:
            # 1. Notion에서 모든 페이지 가져오기
            has_more = True
            next_cursor = None
            notion_page_ids = set()
            
            while has_more:
                response = self.client.query_database(
                    database_id=database.notion_id,
                    start_cursor=next_cursor
                )
                
                for page_data in response['results']:
                    try:
                        notion_page_ids.add(page_data['id'])
                        created, updated = self._sync_page(database, page_data)
                        
                        if created:
                            pages_created += 1
                        elif updated:
                            pages_updated += 1
                        
                        pages_processed += 1
                        
                    except Exception as e:
                        error_msg = f"페이지 동기화 실패 {page_data['id']}: {str(e)}"
                        errors.append(error_msg)
                        sync_history.add_error(page_data['id'], str(e))
                
                has_more = response.get('has_more', False)
                next_cursor = response.get('next_cursor')
            
            # 2. 로컬에만 있는 페이지들 삭제 처리
            local_pages = NotionPage.objects.filter(database=database)
            for local_page in local_pages:
                if local_page.notion_id not in notion_page_ids:
                    local_page.status = NotionPage.PageStatus.DELETED
                    local_page.save()
                    pages_deleted += 1
            
        except Exception as e:
            errors.append(f"전체 동기화 실패: {str(e)}")
        
        duration = (timezone.now() - start_time).total_seconds()
        
        return SyncResult(
            success=len(errors) == 0,
            pages_processed=pages_processed,
            pages_created=pages_created,
            pages_updated=pages_updated,
            pages_deleted=pages_deleted,
            errors=errors,
            duration=duration
        )
    
    def _incremental_sync(self, database: NotionDatabase, sync_history: SyncHistory) -> SyncResult:
        """증분 동기화"""
        start_time = timezone.now()
        pages_processed = 0
        pages_created = 0
        pages_updated = 0
        errors = []
        
        try:
            # 마지막 동기화 이후 수정된 페이지들만 가져오기
            last_sync = database.last_synced or (timezone.now() - timedelta(days=1))
            
            # Notion API는 수정일 기준 필터를 지원하지 않으므로 모든 페이지를 확인
            # 실제 구현에서는 last_edited_time을 비교하여 필요한 페이지만 처리
            response = self.client.query_database(database_id=database.notion_id)
            
            for page_data in response['results']:
                try:
                    # 마지막 수정 시간 확인
                    last_edited = datetime.fromisoformat(
                        page_data['last_edited_time'].replace('Z', '+00:00')
                    )
                    
                    if last_edited > last_sync.replace(tzinfo=None if last_sync.tzinfo is None else last_sync.tzinfo):
                        created, updated = self._sync_page(database, page_data)
                        
                        if created:
                            pages_created += 1
                        elif updated:
                            pages_updated += 1
                        
                        pages_processed += 1
                
                except Exception as e:
                    error_msg = f"페이지 동기화 실패 {page_data['id']}: {str(e)}"
                    errors.append(error_msg)
                    sync_history.add_error(page_data['id'], str(e))
            
        except Exception as e:
            errors.append(f"증분 동기화 실패: {str(e)}")
        
        duration = (timezone.now() - start_time).total_seconds()
        
        return SyncResult(
            success=len(errors) == 0,
            pages_processed=pages_processed,
            pages_created=pages_created,
            pages_updated=pages_updated,
            pages_deleted=0,
            errors=errors,
            duration=duration
        )
    
    def _sync_page(self, database: NotionDatabase, page_data: Dict) -> Tuple[bool, bool]:
        """개별 페이지 동기화"""
        notion_id = page_data['id']
        created = False
        updated = False
        
        try:
            # 페이지 내용 블록 가져오기
            content_blocks = self.client.get_page_content(notion_id)
            
            # 로컬 페이지 조회 또는 생성
            local_page, page_created = NotionPage.objects.get_or_create(
                notion_id=notion_id,
                defaults={
                    'database': database,
                    'title': self._extract_title_from_properties(page_data.get('properties', {})),
                    'properties': page_data.get('properties', {}),
                    'content_blocks': content_blocks,
                    'notion_created_time': datetime.fromisoformat(
                        page_data['created_time'].replace('Z', '+00:00')
                    ),
                    'notion_last_edited_time': datetime.fromisoformat(
                        page_data['last_edited_time'].replace('Z', '+00:00')
                    ),
                    'notion_created_by': page_data.get('created_by', {}).get('id', ''),
                    'notion_last_edited_by': page_data.get('last_edited_by', {}).get('id', ''),
                    'local_hash': '',
                    'status': NotionPage.PageStatus.ACTIVE
                }
            )
            
            if page_created:
                created = True
                logger.debug(f"새 페이지 생성: {notion_id}")
            else:
                # 기존 페이지 업데이트 확인
                notion_last_edited = datetime.fromisoformat(
                    page_data['last_edited_time'].replace('Z', '+00:00')
                )
                
                if notion_last_edited > local_page.notion_last_edited_time.replace(tzinfo=None):
                    # 데이터 업데이트
                    local_page.title = self._extract_title_from_properties(page_data.get('properties', {}))
                    local_page.properties = page_data.get('properties', {})
                    local_page.content_blocks = content_blocks
                    local_page.notion_last_edited_time = notion_last_edited
                    local_page.notion_last_edited_by = page_data.get('last_edited_by', {}).get('id', '')
                    local_page.status = NotionPage.PageStatus.ARCHIVED if page_data.get('archived') else NotionPage.PageStatus.ACTIVE
                    
                    local_page.save()
                    updated = True
                    logger.debug(f"페이지 업데이트: {notion_id}")
            
            # 해시 업데이트
            local_page.local_hash = local_page.calculate_hash()
            local_page.is_dirty = False
            local_page.save(update_fields=['local_hash', 'is_dirty'])
            
        except Exception as e:
            logger.error(f"페이지 동기화 실패 {notion_id}: {str(e)}")
            raise
        
        return created, updated
    
    def _extract_title_from_properties(self, properties: Dict) -> str:
        """페이지 속성에서 제목 추출"""
        # 제목 속성 찾기
        for prop_name, prop_data in properties.items():
            if prop_data.get('type') == 'title':
                title_content = prop_data.get('title', [])
                if title_content:
                    return ''.join([t.get('plain_text', '') for t in title_content])
        
        return "제목 없음"
    
    def push_local_changes(self, database: NotionDatabase) -> SyncResult:
        """로컬 변경사항을 Notion에 반영"""
        start_time = timezone.now()
        pages_processed = 0
        pages_updated = 0
        errors = []
        
        # 변경된 페이지들 가져오기
        dirty_pages = NotionPage.objects.filter(
            database=database,
            is_dirty=True,
            status=NotionPage.PageStatus.ACTIVE
        )
        
        for page in dirty_pages:
            try:
                # Notion에 업데이트 요청
                self.client.update_page(
                    page_id=page.notion_id,
                    properties=page.properties
                )
                
                # 동기화 완료 표시
                page.mark_synced()
                pages_updated += 1
                pages_processed += 1
                
            except Exception as e:
                error_msg = f"페이지 푸시 실패 {page.notion_id}: {str(e)}"
                errors.append(error_msg)
        
        duration = (timezone.now() - start_time).total_seconds()
        
        return SyncResult(
            success=len(errors) == 0,
            pages_processed=pages_processed,
            pages_created=0,
            pages_updated=pages_updated,
            pages_deleted=0,
            errors=errors,
            duration=duration
        )


class NotionCacheService:
    """
    Notion 캐시 서비스
    
    성능 향상을 위한 데이터 캐싱을 관리합니다.
    """
    
    CACHE_TIMEOUT = 300  # 5분
    
    @staticmethod
    def get_database_cache_key(database_id: str) -> str:
        """데이터베이스 캐시 키 생성"""
        return f"notion:db:{database_id}"
    
    @staticmethod
    def get_page_cache_key(page_id: str) -> str:
        """페이지 캐시 키 생성"""
        return f"notion:page:{page_id}"
    
    @staticmethod
    def get_query_cache_key(database_id: str, query_hash: str) -> str:
        """쿼리 결과 캐시 키 생성"""
        return f"notion:query:{database_id}:{query_hash}"
    
    @classmethod
    def cache_database(cls, database_id: str, data: Dict, timeout: Optional[int] = None):
        """데이터베이스 정보 캐싱"""
        cache_key = cls.get_database_cache_key(database_id)
        cache.set(cache_key, data, timeout or cls.CACHE_TIMEOUT)
    
    @classmethod
    def get_cached_database(cls, database_id: str) -> Optional[Dict]:
        """캐시된 데이터베이스 정보 조회"""
        cache_key = cls.get_database_cache_key(database_id)
        return cache.get(cache_key)
    
    @classmethod
    def cache_page(cls, page_id: str, data: Dict, timeout: Optional[int] = None):
        """페이지 정보 캐싱"""
        cache_key = cls.get_page_cache_key(page_id)
        cache.set(cache_key, data, timeout or cls.CACHE_TIMEOUT)
    
    @classmethod
    def get_cached_page(cls, page_id: str) -> Optional[Dict]:
        """캐시된 페이지 정보 조회"""
        cache_key = cls.get_page_cache_key(page_id)
        return cache.get(cache_key)
    
    @classmethod
    def cache_query_result(cls, database_id: str, query_params: Dict, 
                          result: Dict, timeout: Optional[int] = None):
        """쿼리 결과 캐싱"""
        query_hash = hashlib.md5(json.dumps(query_params, sort_keys=True).encode()).hexdigest()
        cache_key = cls.get_query_cache_key(database_id, query_hash)
        cache.set(cache_key, result, timeout or cls.CACHE_TIMEOUT)
    
    @classmethod
    def get_cached_query_result(cls, database_id: str, query_params: Dict) -> Optional[Dict]:
        """캐시된 쿼리 결과 조회"""
        query_hash = hashlib.md5(json.dumps(query_params, sort_keys=True).encode()).hexdigest()
        cache_key = cls.get_query_cache_key(database_id, query_hash)
        return cache.get(cache_key)
    
    @classmethod
    def invalidate_database_cache(cls, database_id: str):
        """데이터베이스 관련 캐시 무효화"""
        # 데이터베이스 캐시 삭제
        db_cache_key = cls.get_database_cache_key(database_id)
        cache.delete(db_cache_key)
        
        # 관련 쿼리 캐시들 삭제 (패턴 매칭)
        cache.delete_pattern(f"notion:query:{database_id}:*")
    
    @classmethod
    def invalidate_page_cache(cls, page_id: str):
        """페이지 캐시 무효화"""
        cache_key = cls.get_page_cache_key(page_id)
        cache.delete(cache_key)
    
    @classmethod
    def clear_all_cache(cls):
        """모든 Notion 관련 캐시 삭제"""
        cache.delete_pattern("notion:*")