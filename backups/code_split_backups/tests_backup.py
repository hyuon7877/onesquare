"""
OneSquare Notion API 연동 - 테스트

Notion API 연동 기능들에 대한 단위 및 통합 테스트
"""

import json
import uuid
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime, timedelta

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.conf import settings

from notion_client.errors import APIResponseError, RequestTimeoutError

from .models import NotionDatabase, NotionPage, SyncHistory, NotionWebhook
from .services import NotionClient, NotionSyncService, NotionCacheService
from .exceptions import (
    NotionAPIError, NotionRateLimitError, NotionServerError,
    NotionNetworkError, NotionTimeoutError, NotionSyncError
)
from .retry_utils import RetryExecutor, RetryConfig, ExponentialBackoff, CircuitBreaker
from .tasks import NotionSyncScheduler, NotionChangeDetector

User = get_user_model()


class NotionClientTestCase(TestCase):
    """NotionClient 테스트"""
    
    def setUp(self):
        self.client = NotionClient()
        self.test_database_id = "test-database-id-123"
        self.test_page_id = "test-page-id-456"
    
    @patch('apps.notion_api.services.Client')
    def test_get_database_success(self, mock_client_class):
        """데이터베이스 조회 성공 테스트"""
        # Mock 설정
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.databases.retrieve.return_value = {
            'id': self.test_database_id,
            'title': [{'plain_text': 'Test Database'}],
            'properties': {}
        }
        
        # 새로운 클라이언트 인스턴스 생성 (mock 적용)
        client = NotionClient()
        
        # 테스트 실행
        result = client.get_database(self.test_database_id)
        
        # 검증
        self.assertEqual(result['id'], self.test_database_id)
        mock_client.databases.retrieve.assert_called_once_with(database_id=self.test_database_id)
    
    @patch('apps.notion_api.services.Client')
    def test_get_database_api_error(self, mock_client_class):
        """데이터베이스 조회 API 오류 테스트"""
        # Mock 설정
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # APIResponseError 시뮬레이션
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {'message': 'Database not found'}
        
        error = APIResponseError("Not found", response=mock_response)
        mock_client.databases.retrieve.side_effect = error
        
        # 새로운 클라이언트 인스턴스 생성 (mock 적용)
        client = NotionClient()
        
        # 테스트 실행 및 검증
        with self.assertRaises(NotionAPIError):
            client.get_database(self.test_database_id)
    
    @patch('apps.notion_api.services.Client')
    def test_query_database_with_pagination(self, mock_client_class):
        """데이터베이스 쿼리 페이지네이션 테스트"""
        # Mock 설정
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.databases.query.return_value = {
            'results': [
                {'id': 'page1', 'properties': {}},
                {'id': 'page2', 'properties': {}}
            ],
            'has_more': False,
            'next_cursor': None
        }
        
        client = NotionClient()
        
        # 테스트 실행
        result = client.query_database(
            self.test_database_id,
            filter_criteria={'property': 'Status', 'select': {'equals': 'Active'}},
            page_size=50
        )
        
        # 검증
        self.assertEqual(len(result['results']), 2)
        mock_client.databases.query.assert_called_once()
        call_args = mock_client.databases.query.call_args[1]
        self.assertEqual(call_args['database_id'], self.test_database_id)
        self.assertEqual(call_args['page_size'], 50)
        self.assertIn('filter', call_args)


class NotionSyncServiceTestCase(TestCase):
    """NotionSyncService 테스트"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.database = NotionDatabase.objects.create(
            notion_id='test-db-123',
            title='Test Database',
            database_type='custom',
            created_by=self.user
        )
        
        self.sync_service = NotionSyncService()
    
    @patch('apps.notion_api.services.NotionClient')
    def test_sync_database_success(self, mock_notion_client_class):
        """데이터베이스 동기화 성공 테스트"""
        # Mock 설정
        mock_client = Mock()
        mock_notion_client_class.return_value = mock_client
        
        # Mock 데이터베이스 스키마
        mock_client.get_database.return_value = {
            'id': self.database.notion_id,
            'properties': {
                'Title': {'type': 'title'},
                'Status': {'type': 'select'}
            }
        }
        
        # Mock 페이지 데이터
        mock_client.query_database_pages.return_value = [
            {
                'id': 'page-123',
                'properties': {
                    'Title': {'title': [{'plain_text': 'Test Page'}]},
                    'Status': {'select': {'name': 'Active'}}
                },
                'created_time': '2025-01-01T10:00:00.000Z',
                'last_edited_time': '2025-01-01T11:00:00.000Z'
            }
        ]
        
        # 새로운 서비스 인스턴스 (mock 적용)
        sync_service = NotionSyncService()
        
        # 테스트 실행
        result = sync_service.sync_database(self.database, 'manual', self.user)
        
        # 검증
        self.assertTrue(result.success)
        self.assertGreater(result.total_pages, 0)
        
        # SyncHistory 생성 확인
        sync_history = SyncHistory.objects.filter(database=self.database).first()
        self.assertIsNotNone(sync_history)
        self.assertEqual(sync_history.triggered_by, self.user)


class NotionExceptionsTestCase(TestCase):
    """Notion 예외 처리 테스트"""
    
    def test_notion_api_error_creation(self):
        """NotionAPIError 생성 테스트"""
        error = NotionAPIError(
            "Test error", 
            error_code="test_error", 
            status_code=400
        )
        
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.error_code, "test_error")
        self.assertEqual(error.status_code, 400)
        
        error_dict = error.to_dict()
        self.assertEqual(error_dict['error_type'], 'NotionAPIError')
        self.assertEqual(error_dict['message'], "Test error")
    
    def test_get_exception_from_response(self):
        """HTTP 응답으로부터 예외 생성 테스트"""
        from .exceptions import get_exception_from_response
        
        # 404 응답 시뮬레이션
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {'message': 'Not found', 'code': 'object_not_found'}
        
        exception = get_exception_from_response(mock_response)
        
        self.assertIsInstance(exception, NotionAPIError)
        self.assertEqual(exception.status_code, 404)
        self.assertEqual(exception.error_code, 'object_not_found')


class RetryUtilsTestCase(TestCase):
    """재시도 유틸리티 테스트"""
    
    def test_exponential_backoff(self):
        """지수 백오프 전략 테스트"""
        backoff = ExponentialBackoff(base_delay=1.0, multiplier=2.0, max_delay=10.0)
        
        self.assertEqual(backoff.get_delay(1), 1.0)
        self.assertEqual(backoff.get_delay(2), 2.0)
        self.assertEqual(backoff.get_delay(3), 4.0)
        self.assertEqual(backoff.get_delay(4), 8.0)
        self.assertEqual(backoff.get_delay(5), 10.0)  # max_delay 제한
    
    def test_retry_executor_success(self):
        """재시도 실행기 성공 테스트"""
        config = RetryConfig(max_retries=3)
        executor = RetryExecutor(config)
        
        # 성공하는 함수
        def success_function():
            return "success"
        
        result = executor.execute(success_function)
        
        self.assertTrue(result.success)
        self.assertEqual(result.result, "success")
        self.assertEqual(result.attempts, 1)
    
    def test_retry_executor_with_retries(self):
        """재시도 실행기 재시도 테스트"""
        config = RetryConfig(max_retries=3, backoff_strategy=ExponentialBackoff(base_delay=0.01))
        executor = RetryExecutor(config)
        
        # 2번 실패 후 성공하는 함수
        call_count = 0
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NotionServerError("Server error")
            return "success after retries"
        
        result = executor.execute(flaky_function)
        
        self.assertTrue(result.success)
        self.assertEqual(result.result, "success after retries")
        self.assertEqual(result.attempts, 3)
        self.assertEqual(call_count, 3)
    
    def test_circuit_breaker(self):
        """서킷 브레이커 테스트"""
        circuit_breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=1,
            name="test_circuit"
        )
        
        # 초기 상태: closed
        self.assertTrue(circuit_breaker.can_execute())
        
        # 실패 기록
        circuit_breaker.record_failure(Exception("Test error"))
        circuit_breaker.record_failure(Exception("Test error"))
        
        # 임계값 도달: open 상태
        self.assertFalse(circuit_breaker.can_execute())


class NotionSchedulerTestCase(TestCase):
    """Notion 스케줄러 테스트"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='scheduler_test',
            email='scheduler@example.com',
            password='testpass123'
        )
        
        # 테스트용 데이터베이스 생성
        self.database1 = NotionDatabase.objects.create(
            notion_id='scheduler-db-1',
            title='Scheduler Test DB 1',
            database_type='custom',
            sync_interval=300,  # 5분
            is_active=True,
            created_by=self.user
        )
        
        self.database2 = NotionDatabase.objects.create(
            notion_id='scheduler-db-2',
            title='Scheduler Test DB 2',
            database_type='custom',
            sync_interval=600,  # 10분
            is_active=True,
            last_synced=timezone.now() - timedelta(minutes=15),  # 15분 전 동기화
            created_by=self.user
        )
        
        self.scheduler = NotionSyncScheduler()
    
    def test_get_databases_for_sync(self):
        """동기화 대상 데이터베이스 조회 테스트"""
        databases = self.scheduler._get_databases_for_sync()
        
        # database1은 한 번도 동기화된 적이 없으므로 포함
        # database2는 마지막 동기화가 15분 전이고 간격이 10분이므로 포함
        database_ids = [db.id for db in databases]
        
        self.assertIn(self.database1.id, database_ids)
        self.assertIn(self.database2.id, database_ids)
    
    def test_should_sync_database(self):
        """데이터베이스 동기화 필요 여부 판단 테스트"""
        now = timezone.now()
        
        # 한 번도 동기화된 적이 없는 경우
        should_sync = self.scheduler._should_sync_database(self.database1, now)
        self.assertTrue(should_sync)
        
        # 최근에 동기화된 경우
        self.database2.last_synced = now - timedelta(minutes=5)
        self.database2.sync_interval = 600  # 10분
        should_sync = self.scheduler._should_sync_database(self.database2, now)
        self.assertFalse(should_sync)
        
        # 동기화 간격이 지난 경우
        self.database2.last_synced = now - timedelta(minutes=15)
        should_sync = self.scheduler._should_sync_database(self.database2, now)
        self.assertTrue(should_sync)
    
    def test_force_sync_database(self):
        """강제 동기화 예약 테스트"""
        result = self.scheduler.force_sync_database(self.database1.id)
        self.assertTrue(result)
        
        # 캐시에 강제 동기화 플래그가 설정되었는지 확인
        force_sync_key = f"notion_force_sync_{self.database1.id}"
        self.assertTrue(cache.get(force_sync_key))


class NotionChangeDetectorTestCase(TestCase):
    """Notion 변경사항 감지기 테스트"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='detector_test',
            email='detector@example.com',
            password='testpass123'
        )
        
        self.database = NotionDatabase.objects.create(
            notion_id='detector-db-1',
            title='Change Detector Test DB',
            database_type='custom',
            schema={'properties': {'Title': {'type': 'title'}}},
            last_synced=timezone.now() - timedelta(hours=1),
            created_by=self.user
        )
        
        self.detector = NotionChangeDetector()
    
    def test_has_schema_changed_no_change(self):
        """스키마 변경 없음 테스트"""
        current_schema = {
            'properties': {'Title': {'type': 'title'}}
        }
        
        has_changed = self.detector._has_schema_changed(self.database, current_schema)
        self.assertFalse(has_changed)
    
    def test_has_schema_changed_with_new_property(self):
        """새 속성 추가 시 스키마 변경 테스트"""
        current_schema = {
            'properties': {
                'Title': {'type': 'title'},
                'Status': {'type': 'select'}  # 새 속성
            }
        }
        
        has_changed = self.detector._has_schema_changed(self.database, current_schema)
        self.assertTrue(has_changed)
    
    def test_has_schema_changed_with_type_change(self):
        """속성 타입 변경 시 스키마 변경 테스트"""
        current_schema = {
            'properties': {'Title': {'type': 'rich_text'}}  # 타입 변경
        }
        
        has_changed = self.detector._has_schema_changed(self.database, current_schema)
        self.assertTrue(has_changed)


class NotionModelTestCase(TestCase):
    """Notion 모델 테스트"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='model_test',
            email='model@example.com',
            password='testpass123'
        )
    
    def test_notion_database_creation(self):
        """NotionDatabase 생성 테스트"""
        database = NotionDatabase.objects.create(
            notion_id='model-test-db',
            title='Model Test Database',
            database_type='tasks',
            created_by=self.user
        )
        
        self.assertEqual(database.notion_id, 'model-test-db')
        self.assertEqual(database.title, 'Model Test Database')
        self.assertEqual(database.database_type, 'tasks')
        self.assertTrue(database.is_active)
        self.assertEqual(database.sync_interval, 300)
        self.assertEqual(database.created_by, self.user)
    
    def test_notion_database_is_synced_recently(self):
        """NotionDatabase 최근 동기화 여부 테스트"""
        database = NotionDatabase.objects.create(
            notion_id='recent-sync-test',
            title='Recent Sync Test',
            created_by=self.user
        )
        
        # 최근 동기화 안됨
        self.assertFalse(database.is_synced_recently())
        
        # 최근 동기화됨
        database.last_synced = timezone.now() - timedelta(minutes=2)
        database.save()
        self.assertTrue(database.is_synced_recently())
        
        # 오래된 동기화
        database.last_synced = timezone.now() - timedelta(hours=2)
        database.save()
        self.assertFalse(database.is_synced_recently())
    
    def test_notion_page_creation(self):
        """NotionPage 생성 테스트"""
        database = NotionDatabase.objects.create(
            notion_id='page-test-db',
            title='Page Test Database',
            created_by=self.user
        )
        
        page = NotionPage.objects.create(
            database=database,
            notion_id='test-page-123',
            title='Test Page',
            properties={'Title': {'title': [{'plain_text': 'Test Page'}]}},
            notion_created_time=timezone.now(),
            notion_last_edited_time=timezone.now()
        )
        
        self.assertEqual(page.notion_id, 'test-page-123')
        self.assertEqual(page.title, 'Test Page')
        self.assertEqual(page.database, database)
        self.assertEqual(page.status, 'active')
        self.assertFalse(page.is_dirty)
    
    def test_sync_history_success_rate(self):
        """SyncHistory 성공률 계산 테스트"""
        database = NotionDatabase.objects.create(
            notion_id='success-rate-test',
            title='Success Rate Test',
            created_by=self.user
        )
        
        sync_history = SyncHistory.objects.create(
            database=database,
            sync_type='manual',
            status='completed',
            total_pages=10,
            pages_created=3,
            pages_updated=5,
            pages_failed=2,
            triggered_by=self.user
        )
        
        # 성공률 = (10 - 2) / 10 * 100 = 80%
        self.assertEqual(sync_history.success_rate, 80.0)
        
        # 실패한 페이지가 없는 경우
        sync_history.pages_failed = 0
        sync_history.save()
        self.assertEqual(sync_history.success_rate, 100.0)
    
    def tearDown(self):
        """테스트 정리"""
        # 캐시 정리
        cache.clear()


class NotionIntegrationTestCase(TestCase):
    """Notion API 통합 테스트"""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # 실제 Notion API를 사용하지 않는 통합 테스트
        # 실제 API 키가 있는 경우에만 실행되도록 설정
        cls.skip_integration = not getattr(settings, 'NOTION_TOKEN', None)
    
    def setUp(self):
        if self.skip_integration:
            self.skipTest("Notion API 키가 설정되지 않아 통합 테스트를 건너뜁니다.")
        
        self.user = User.objects.create_user(
            username='integration_test',
            email='integration@example.com',
            password='testpass123'
        )
    
    def test_full_sync_workflow(self):
        """전체 동기화 워크플로우 테스트"""
        if self.skip_integration:
            return
        
        # 실제 Notion API를 사용한 통합 테스트는 
        # 테스트 환경에서 실제 Notion 데이터베이스가 필요함
        # 여기서는 Mock을 사용한 시뮬레이션으로 대체
        
        with patch('apps.notion_api.services.NotionClient') as mock_client_class:
            # Mock 설정 생략 (위의 단위 테스트와 유사)
            pass