"""
OneSquare 매출 관리 - Notion API 동기화 서비스
실시간 양방향 데이터 동기화 및 충돌 해결
"""

import logging
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from notion_client import Client
from notion_client.errors import APIResponseError

from .models import RevenueRecord, Client, Project, RevenueCategory
from .permissions import RevenuePermissionManager, UserRole

logger = logging.getLogger(__name__)

class NotionRevenueSync:
    """Notion API를 통한 매출 데이터 동기화 서비스"""
    
    def __init__(self):
        self.notion_client = None
        self.database_id = None
        self.sync_status_cache_key = 'revenue_notion_sync_status'
        self.last_sync_cache_key = 'revenue_notion_last_sync'
        
        self._initialize_notion_client()
    
    def _initialize_notion_client(self):
        """Notion 클라이언트 초기화"""
        try:
            notion_token = getattr(settings, 'NOTION_TOKEN', None)
            self.database_id = getattr(settings, 'NOTION_REVENUE_DATABASE_ID', None)
            
            if not notion_token or not self.database_id:
                logger.error("Notion API 설정이 누락되었습니다. (NOTION_TOKEN, NOTION_REVENUE_DATABASE_ID)")
                return False
            
            self.notion_client = Client(auth=notion_token)
            logger.info("Notion 클라이언트 초기화 완료")
            return True
            
        except Exception as e:
            logger.error(f"Notion 클라이언트 초기화 실패: {e}")
            return False
    
    def is_sync_available(self) -> bool:
        """동기화 서비스 사용 가능 여부 확인"""
        return self.notion_client is not None and self.database_id is not None
    
    async def sync_all_revenue_data(self, user=None) -> Dict:
        """전체 매출 데이터 동기화 (관리자만 가능)"""
        if not self.is_sync_available():
            return {'success': False, 'message': 'Notion API 설정이 필요합니다.'}
        
        # 권한 확인
        if user:
            user_role = RevenuePermissionManager.get_user_role(user)
            if user_role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
                return {'success': False, 'message': '전체 동기화 권한이 없습니다.'}
        
        try:
            # 동기화 상태 설정
            cache.set(self.sync_status_cache_key, 'running', timeout=300)  # 5분
            
            # Notion에서 데이터 가져오기
            notion_data = await self._fetch_notion_revenue_data()
            
            # Django에서 데이터 가져오기
            django_data = self._fetch_django_revenue_data()
            
            # 데이터 동기화 수행
            sync_result = await self._perform_bidirectional_sync(notion_data, django_data)
            
            # 마지막 동기화 시간 기록
            cache.set(self.last_sync_cache_key, timezone.now().isoformat(), timeout=None)
            cache.set(self.sync_status_cache_key, 'completed', timeout=60)
            
            logger.info(f"전체 동기화 완료: {sync_result}")
            return {
                'success': True,
                'message': '동기화가 완료되었습니다.',
                'result': sync_result
            }
            
        except Exception as e:
            logger.error(f"전체 동기화 실패: {e}")
            cache.set(self.sync_status_cache_key, f'error: {str(e)}', timeout=300)
            return {'success': False, 'message': f'동기화 실패: {str(e)}'}
    
    async def sync_single_revenue(self, revenue_id: str, direction: str = 'both') -> Dict:
        """단일 매출 데이터 동기화
        
        Args:
            revenue_id: 매출 기록 ID (Django UUID 또는 Notion Page ID)
            direction: 'django_to_notion', 'notion_to_django', 'both'
        """
        if not self.is_sync_available():
            return {'success': False, 'message': 'Notion API 설정이 필요합니다.'}
        
        try:
            if direction in ['django_to_notion', 'both']:
                # Django -> Notion 동기화
                django_result = await self._sync_django_to_notion(revenue_id)
                
            if direction in ['notion_to_django', 'both']:
                # Notion -> Django 동기화
                notion_result = await self._sync_notion_to_django(revenue_id)
            
            return {
                'success': True,
                'message': '개별 동기화가 완료되었습니다.',
                'django_to_notion': django_result if direction != 'notion_to_django' else None,
                'notion_to_django': notion_result if direction != 'django_to_notion' else None
            }
            
        except Exception as e:
            logger.error(f"개별 동기화 실패 ({revenue_id}): {e}")
            return {'success': False, 'message': f'동기화 실패: {str(e)}'}
    
    async def _fetch_notion_revenue_data(self) -> List[Dict]:
        """Notion 데이터베이스에서 매출 데이터 조회"""
        try:
            all_pages = []
            start_cursor = None
            
            while True:
                query_params = {
                    "database_id": self.database_id,
                    "page_size": 100
                }
                
                if start_cursor:
                    query_params["start_cursor"] = start_cursor
                
                response = self.notion_client.databases.query(**query_params)
                all_pages.extend(response.get('results', []))
                
                if not response.get('has_more', False):
                    break
                    
                start_cursor = response.get('next_cursor')
            
            logger.info(f"Notion에서 {len(all_pages)}개 매출 데이터 조회 완료")
            return all_pages
            
        except APIResponseError as e:
            logger.error(f"Notion 데이터 조회 실패: {e}")
            raise
    
    def _fetch_django_revenue_data(self) -> List[Dict]:
        """Django에서 매출 데이터 조회"""
        try:
            revenues = RevenueRecord.objects.select_related(
                'project', 'client', 'category', 'sales_person'
            ).all()
            
            django_data = []
            for revenue in revenues:
                data = {
                    'id': str(revenue.id),
                    'project': revenue.project.name,
                    'project_code': revenue.project.code,
                    'client': revenue.client.name,
                    'client_code': revenue.client.code,
                    'category': revenue.category.name,
                    'revenue_type': revenue.revenue_type,
                    'amount': float(revenue.amount),
                    'tax_amount': float(revenue.tax_amount),
                    'net_amount': float(revenue.net_amount),
                    'revenue_date': revenue.revenue_date.isoformat(),
                    'payment_status': revenue.payment_status,
                    'is_confirmed': revenue.is_confirmed,
                    'sales_person': revenue.sales_person.get_full_name() if revenue.sales_person else '',
                    'description': revenue.description or '',
                    'due_date': revenue.due_date.isoformat() if revenue.due_date else None,
                    'payment_date': revenue.payment_date.isoformat() if revenue.payment_date else None,
                    'updated_at': revenue.updated_at.isoformat(),
                    'notion_page_id': getattr(revenue, 'notion_page_id', None)
                }
                django_data.append(data)
            
            logger.info(f"Django에서 {len(django_data)}개 매출 데이터 조회 완료")
            return django_data
            
        except Exception as e:
            logger.error(f"Django 데이터 조회 실패: {e}")
            raise
    
    async def _perform_bidirectional_sync(self, notion_data: List[Dict], django_data: List[Dict]) -> Dict:
        """양방향 동기화 수행"""
        sync_result = {
            'django_created': 0,
            'django_updated': 0,
            'notion_created': 0,
            'notion_updated': 0,
            'conflicts_resolved': 0,
            'errors': []
        }
        
        # Django 데이터 매핑 (notion_page_id 기준)
        django_by_notion_id = {}
        django_by_internal_id = {}
        
        for item in django_data:
            django_by_internal_id[item['id']] = item
            if item.get('notion_page_id'):
                django_by_notion_id[item['notion_page_id']] = item
        
        # Notion 데이터 처리
        for notion_item in notion_data:
            notion_id = notion_item['id']
            
            try:
                # Notion 데이터 파싱
                parsed_notion = self._parse_notion_revenue_item(notion_item)
                
                if notion_id in django_by_notion_id:
                    # 기존 레코드 업데이트
                    django_item = django_by_notion_id[notion_id]
                    if self._needs_update(parsed_notion, django_item, 'notion_to_django'):
                        await self._update_django_from_notion(django_item['id'], parsed_notion)
                        sync_result['django_updated'] += 1
                else:
                    # 새 레코드 생성
                    await self._create_django_from_notion(parsed_notion, notion_id)
                    sync_result['django_created'] += 1
                    
            except Exception as e:
                error_msg = f"Notion 아이템 {notion_id} 처리 실패: {str(e)}"
                logger.error(error_msg)
                sync_result['errors'].append(error_msg)
        
        # Django 데이터 처리 (Notion에 없는 것들)
        for django_item in django_data:
            if not django_item.get('notion_page_id'):
                # Notion에 새로 생성
                try:
                    notion_page_id = await self._create_notion_from_django(django_item)
                    await self._update_django_notion_id(django_item['id'], notion_page_id)
                    sync_result['notion_created'] += 1
                except Exception as e:
                    error_msg = f"Django 아이템 {django_item['id']} Notion 생성 실패: {str(e)}"
                    logger.error(error_msg)
                    sync_result['errors'].append(error_msg)
        
        return sync_result
    
    def _parse_notion_revenue_item(self, notion_item: Dict) -> Dict:
        """Notion 페이지 데이터를 Django 형식으로 파싱"""
        properties = notion_item.get('properties', {})
        
        try:
            # 각 Notion 프로퍼티 타입별 파싱
            parsed = {
                'notion_id': notion_item['id'],
                'project_name': self._get_notion_text(properties.get('프로젝트')),
                'project_code': self._get_notion_text(properties.get('프로젝트코드')),
                'client_name': self._get_notion_text(properties.get('고객명')),
                'client_code': self._get_notion_text(properties.get('고객코드')),
                'category_name': self._get_notion_text(properties.get('카테고리')),
                'revenue_type': self._get_notion_select(properties.get('매출유형')),
                'amount': self._get_notion_number(properties.get('금액')),
                'tax_amount': self._get_notion_number(properties.get('세금')),
                'net_amount': self._get_notion_number(properties.get('순매출')),
                'revenue_date': self._get_notion_date(properties.get('매출일')),
                'payment_status': self._get_notion_select(properties.get('결제상태')),
                'is_confirmed': self._get_notion_checkbox(properties.get('확정여부')),
                'sales_person': self._get_notion_text(properties.get('영업담당')),
                'description': self._get_notion_text(properties.get('설명')),
                'due_date': self._get_notion_date(properties.get('결제예정일')),
                'payment_date': self._get_notion_date(properties.get('결제일')),
                'updated_at': notion_item.get('last_edited_time')
            }
            
            return parsed
            
        except Exception as e:
            logger.error(f"Notion 데이터 파싱 실패: {e}")
            raise
    
    def _get_notion_text(self, prop) -> str:
        """Notion 텍스트 프로퍼티 추출"""
        if not prop or prop.get('type') not in ['title', 'rich_text']:
            return ''
        
        text_array = prop.get('title', []) or prop.get('rich_text', [])
        return ''.join([item.get('text', {}).get('content', '') for item in text_array])
    
    def _get_notion_number(self, prop) -> Decimal:
        """Notion 숫자 프로퍼티 추출"""
        if not prop or prop.get('type') != 'number':
            return Decimal('0')
        return Decimal(str(prop.get('number', 0)))
    
    def _get_notion_date(self, prop) -> Optional[str]:
        """Notion 날짜 프로퍼티 추출"""
        if not prop or prop.get('type') != 'date':
            return None
        
        date_obj = prop.get('date')
        if date_obj:
            return date_obj.get('start')
        return None
    
    def _get_notion_select(self, prop) -> str:
        """Notion 선택 프로퍼티 추출"""
        if not prop or prop.get('type') != 'select':
            return ''
        
        select_obj = prop.get('select')
        if select_obj:
            return select_obj.get('name', '')
        return ''
    
    def _get_notion_checkbox(self, prop) -> bool:
        """Notion 체크박스 프로퍼티 추출"""
        if not prop or prop.get('type') != 'checkbox':
            return False
        return prop.get('checkbox', False)
    
    def _needs_update(self, source_data: Dict, target_data: Dict, direction: str) -> bool:
        """업데이트 필요 여부 판단 (타임스탬프 기준)"""
        try:
            if direction == 'notion_to_django':
                notion_updated = datetime.fromisoformat(source_data['updated_at'].replace('Z', '+00:00'))
                django_updated = datetime.fromisoformat(target_data['updated_at'])
                return notion_updated > django_updated
            else:
                django_updated = datetime.fromisoformat(source_data['updated_at'])
                notion_updated = datetime.fromisoformat(target_data['updated_at'].replace('Z', '+00:00'))
                return django_updated > notion_updated
        except (KeyError, ValueError) as e:
            logger.warning(f"타임스탬프 비교 실패, 강제 업데이트: {e}")
            return True
    
    async def _create_django_from_notion(self, notion_data: Dict, notion_page_id: str):
        """Notion 데이터로 Django 레코드 생성"""
        try:
            # 연관 객체들 찾기/생성
            project = await self._get_or_create_project(
                notion_data['project_name'], 
                notion_data.get('project_code', '')
            )
            
            client = await self._get_or_create_client(
                notion_data['client_name'], 
                notion_data.get('client_code', '')
            )
            
            category = await self._get_or_create_category(notion_data['category_name'])
            
            # RevenueRecord 생성
            revenue = RevenueRecord.objects.create(
                project=project,
                client=client,
                category=category,
                revenue_type=notion_data.get('revenue_type', 'other'),
                amount=notion_data.get('amount', Decimal('0')),
                tax_amount=notion_data.get('tax_amount', Decimal('0')),
                net_amount=notion_data.get('net_amount', Decimal('0')),
                revenue_date=notion_data.get('revenue_date') or timezone.now().date(),
                payment_status=notion_data.get('payment_status', 'pending'),
                is_confirmed=notion_data.get('is_confirmed', False),
                description=notion_data.get('description', ''),
                due_date=notion_data.get('due_date'),
                payment_date=notion_data.get('payment_date'),
                notion_page_id=notion_page_id
            )
            
            logger.info(f"Notion에서 Django 레코드 생성: {revenue.id}")
            
        except Exception as e:
            logger.error(f"Django 레코드 생성 실패: {e}")
            raise
    
    async def _update_django_from_notion(self, django_id: str, notion_data: Dict):
        """Notion 데이터로 Django 레코드 업데이트"""
        try:
            revenue = RevenueRecord.objects.get(id=django_id)
            
            # 필요한 연관 객체들 업데이트
            if notion_data.get('project_name'):
                project = await self._get_or_create_project(
                    notion_data['project_name'], 
                    notion_data.get('project_code', '')
                )
                revenue.project = project
            
            if notion_data.get('client_name'):
                client = await self._get_or_create_client(
                    notion_data['client_name'], 
                    notion_data.get('client_code', '')
                )
                revenue.client = client
            
            if notion_data.get('category_name'):
                category = await self._get_or_create_category(notion_data['category_name'])
                revenue.category = category
            
            # 필드 업데이트
            revenue.revenue_type = notion_data.get('revenue_type', revenue.revenue_type)
            revenue.amount = notion_data.get('amount', revenue.amount)
            revenue.tax_amount = notion_data.get('tax_amount', revenue.tax_amount)
            revenue.net_amount = notion_data.get('net_amount', revenue.net_amount)
            
            if notion_data.get('revenue_date'):
                revenue.revenue_date = notion_data['revenue_date']
            
            revenue.payment_status = notion_data.get('payment_status', revenue.payment_status)
            revenue.is_confirmed = notion_data.get('is_confirmed', revenue.is_confirmed)
            revenue.description = notion_data.get('description', revenue.description)
            
            if notion_data.get('due_date'):
                revenue.due_date = notion_data['due_date']
            if notion_data.get('payment_date'):
                revenue.payment_date = notion_data['payment_date']
            
            revenue.save()
            logger.info(f"Django 레코드 업데이트: {django_id}")
            
        except RevenueRecord.DoesNotExist:
            logger.error(f"업데이트할 Django 레코드 없음: {django_id}")
            raise
        except Exception as e:
            logger.error(f"Django 레코드 업데이트 실패: {e}")
            raise
    
    async def _create_notion_from_django(self, django_data: Dict) -> str:
        """Django 데이터로 Notion 페이지 생성"""
        try:
            # Notion 페이지 프로퍼티 구성
            properties = {
                "프로젝트": {
                    "title": [{"text": {"content": django_data.get('project', '')}}]
                },
                "프로젝트코드": {
                    "rich_text": [{"text": {"content": django_data.get('project_code', '')}}]
                },
                "고객명": {
                    "rich_text": [{"text": {"content": django_data.get('client', '')}}]
                },
                "고객코드": {
                    "rich_text": [{"text": {"content": django_data.get('client_code', '')}}]
                },
                "카테고리": {
                    "rich_text": [{"text": {"content": django_data.get('category', '')}}]
                },
                "매출유형": {
                    "select": {"name": django_data.get('revenue_type', 'other')}
                },
                "금액": {
                    "number": float(django_data.get('amount', 0))
                },
                "세금": {
                    "number": float(django_data.get('tax_amount', 0))
                },
                "순매출": {
                    "number": float(django_data.get('net_amount', 0))
                },
                "매출일": {
                    "date": {"start": django_data.get('revenue_date', '')}
                },
                "결제상태": {
                    "select": {"name": django_data.get('payment_status', 'pending')}
                },
                "확정여부": {
                    "checkbox": django_data.get('is_confirmed', False)
                },
                "영업담당": {
                    "rich_text": [{"text": {"content": django_data.get('sales_person', '')}}]
                },
                "설명": {
                    "rich_text": [{"text": {"content": django_data.get('description', '')}}]
                }
            }
            
            # 선택적 필드들
            if django_data.get('due_date'):
                properties["결제예정일"] = {"date": {"start": django_data['due_date']}}
            
            if django_data.get('payment_date'):
                properties["결제일"] = {"date": {"start": django_data['payment_date']}}
            
            # Notion 페이지 생성
            response = self.notion_client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            
            notion_page_id = response['id']
            logger.info(f"Notion 페이지 생성 완료: {notion_page_id}")
            return notion_page_id
            
        except APIResponseError as e:
            logger.error(f"Notion 페이지 생성 실패: {e}")
            raise
        except Exception as e:
            logger.error(f"Notion 페이지 생성 중 오류: {e}")
            raise
    
    async def _update_django_notion_id(self, django_id: str, notion_page_id: str):
        """Django 레코드에 Notion 페이지 ID 업데이트"""
        try:
            revenue = RevenueRecord.objects.get(id=django_id)
            revenue.notion_page_id = notion_page_id
            revenue.save()
            logger.info(f"Django 레코드 {django_id}에 Notion ID {notion_page_id} 연결")
        except Exception as e:
            logger.error(f"Notion ID 업데이트 실패: {e}")
            raise
    
    async def _get_or_create_project(self, name: str, code: str = '') -> Project:
        """프로젝트 찾기 또는 생성"""
        try:
            return Project.objects.get(name=name)
        except Project.DoesNotExist:
            return Project.objects.create(
                name=name,
                code=code or name[:10],
                description=f"Notion 동기화로 생성: {name}"
            )
    
    async def _get_or_create_client(self, name: str, code: str = '') -> Client:
        """고객 찾기 또는 생성"""
        try:
            return Client.objects.get(name=name)
        except Client.DoesNotExist:
            return Client.objects.create(
                name=name,
                code=code or name[:10],
                contact_person=name,
                is_active=True
            )
    
    async def _get_or_create_category(self, name: str) -> RevenueCategory:
        """카테고리 찾기 또는 생성"""
        try:
            return RevenueCategory.objects.get(name=name)
        except RevenueCategory.DoesNotExist:
            return RevenueCategory.objects.create(
                name=name,
                code=name.lower().replace(' ', '_'),
                description=f"Notion 동기화로 생성: {name}",
                is_active=True
            )
    
    def get_sync_status(self) -> Dict:
        """동기화 상태 조회"""
        status = cache.get(self.sync_status_cache_key, 'idle')
        last_sync = cache.get(self.last_sync_cache_key, None)
        
        return {
            'status': status,
            'last_sync': last_sync,
            'is_available': self.is_sync_available(),
            'database_id': self.database_id[:8] + '...' if self.database_id else None
        }
    
    def clear_sync_cache(self):
        """동기화 캐시 초기화"""
        cache.delete(self.sync_status_cache_key)
        cache.delete(self.last_sync_cache_key)
        logger.info("동기화 캐시 초기화 완료")


# 백그라운드 동기화 작업을 위한 헬퍼 함수들
def schedule_revenue_sync():
    """정기 동기화 작업 스케줄링 (Celery 등에서 사용)"""
    pass

def handle_revenue_webhook(webhook_data: Dict):
    """Notion 웹훅 처리 (실시간 동기화)"""
    pass