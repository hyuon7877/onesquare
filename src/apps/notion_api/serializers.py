"""
OneSquare Notion API 연동 - Serializers

이 모듈은 Notion API 관련 데이터의 직렬화를 담당합니다.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import NotionDatabase, NotionPage, SyncHistory, NotionWebhook

User = get_user_model()


class NotionDatabaseSerializer(serializers.ModelSerializer):
    """Notion 데이터베이스 직렬화"""
    
    database_type_display = serializers.CharField(source='get_database_type_display', read_only=True)
    is_synced_recently = serializers.BooleanField(read_only=True)
    pages_count = serializers.SerializerMethodField()
    last_sync_status = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = NotionDatabase
        fields = [
            'id', 'notion_id', 'title', 'description', 'database_type',
            'database_type_display', 'schema', 'is_active', 'sync_interval',
            'last_synced', 'is_synced_recently', 'pages_count', 'last_sync_status',
            'created_at', 'updated_at', 'created_by', 'created_by_username'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'last_synced']
    
    def get_pages_count(self, obj):
        """페이지 수 계산"""
        return obj.pages.filter(status='active').count()
    
    def get_last_sync_status(self, obj):
        """마지막 동기화 상태"""
        last_sync = obj.sync_history.order_by('-started_at').first()
        if last_sync:
            return {
                'status': last_sync.status,
                'started_at': last_sync.started_at,
                'pages_processed': last_sync.total_pages,
                'success_rate': last_sync.success_rate
            }
        return None
    
    def validate_notion_id(self, value):
        """Notion ID 형식 검증"""
        if len(value) != 32:
            raise serializers.ValidationError("Notion 데이터베이스 ID는 32자여야 합니다.")
        return value
    
    def validate_sync_interval(self, value):
        """동기화 간격 검증"""
        if value < 60:
            raise serializers.ValidationError("동기화 간격은 최소 60초 이상이어야 합니다.")
        return value


class NotionPageSerializer(serializers.ModelSerializer):
    """Notion 페이지 직렬화"""
    
    database_title = serializers.CharField(source='database.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    has_conflicts = serializers.SerializerMethodField()
    content_preview = serializers.SerializerMethodField()
    
    class Meta:
        model = NotionPage
        fields = [
            'id', 'notion_id', 'database', 'database_title', 'title', 'status',
            'status_display', 'properties', 'content_blocks', 'content_preview',
            'notion_created_time', 'notion_last_edited_time', 'notion_created_by',
            'notion_last_edited_by', 'local_hash', 'is_dirty', 'has_conflicts',
            'sync_conflicts', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'notion_created_time', 'notion_last_edited_time',
            'notion_created_by', 'notion_last_edited_by', 'local_hash',
            'created_at', 'updated_at'
        ]
    
    def get_has_conflicts(self, obj):
        """동기화 충돌 여부"""
        return len(obj.sync_conflicts) > 0
    
    def get_content_preview(self, obj):
        """내용 미리보기 (첫 번째 블록의 텍스트)"""
        if obj.content_blocks:
            for block in obj.content_blocks[:3]:  # 처음 3개 블록만
                if block.get('type') == 'paragraph':
                    rich_text = block.get('paragraph', {}).get('rich_text', [])
                    if rich_text:
                        return ''.join([t.get('plain_text', '') for t in rich_text])[:200]
        return ""


class NotionPageUpdateSerializer(serializers.Serializer):
    """Notion 페이지 업데이트 요청"""
    
    properties = serializers.JSONField(required=True)
    
    def validate_properties(self, value):
        """속성 데이터 검증"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("속성 데이터는 객체 형태여야 합니다.")
        
        if not value:
            raise serializers.ValidationError("최소 하나의 속성이 필요합니다.")
        
        return value


class SyncHistorySerializer(serializers.ModelSerializer):
    """동기화 기록 직렬화"""
    
    database_title = serializers.CharField(source='database.title', read_only=True)
    sync_type_display = serializers.CharField(source='get_sync_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    triggered_by_username = serializers.CharField(source='triggered_by.username', read_only=True)
    success_rate = serializers.FloatField(read_only=True)
    duration_seconds = serializers.SerializerMethodField()
    
    class Meta:
        model = SyncHistory
        fields = [
            'id', 'sync_id', 'database', 'database_title', 'sync_type',
            'sync_type_display', 'status', 'status_display', 'started_at',
            'completed_at', 'duration', 'duration_seconds', 'total_pages',
            'pages_created', 'pages_updated', 'pages_deleted', 'pages_failed',
            'success_rate', 'error_message', 'error_details',
            'triggered_by', 'triggered_by_username'
        ]
        read_only_fields = [
            'id', 'sync_id', 'started_at', 'completed_at', 'duration',
            'success_rate'
        ]
    
    def get_duration_seconds(self, obj):
        """동기화 소요 시간 (초)"""
        if obj.duration:
            return obj.duration.total_seconds()
        return None


class DatabaseSyncRequestSerializer(serializers.Serializer):
    """데이터베이스 동기화 요청"""
    
    SYNC_TYPE_CHOICES = [
        ('full_sync', '전체 동기화'),
        ('incremental', '증분 동기화'),
        ('manual', '수동 동기화'),
    ]
    
    sync_type = serializers.ChoiceField(
        choices=SYNC_TYPE_CHOICES,
        default='incremental',
        help_text="동기화 유형"
    )
    force_sync = serializers.BooleanField(
        default=False,
        help_text="진행 중인 동기화가 있어도 강제 실행"
    )


class NotionWebhookSerializer(serializers.ModelSerializer):
    """Notion 웹훅 직렬화"""
    
    database_title = serializers.CharField(source='database.title', read_only=True)
    
    class Meta:
        model = NotionWebhook
        fields = [
            'id', 'webhook_id', 'database', 'database_title', 'event_types',
            'is_active', 'total_calls', 'last_called', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'total_calls', 'last_called', 'created_at', 'updated_at']


class NotionWorkspaceSearchSerializer(serializers.Serializer):
    """Notion 워크스페이스 검색 요청"""
    
    query = serializers.CharField(max_length=200, allow_blank=True, default='')
    object_type = serializers.ChoiceField(
        choices=[('page', '페이지'), ('database', '데이터베이스'), ('all', '모두')],
        default='page'
    )
    page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)


class NotionPropertySerializer(serializers.Serializer):
    """Notion 속성 직렬화 (동적 스키마)"""
    
    def to_representation(self, instance):
        """속성 타입에 따른 동적 직렬화"""
        if not isinstance(instance, dict):
            return instance
        
        property_type = instance.get('type')
        
        # 각 속성 타입별 처리
        if property_type == 'title':
            return {
                'type': 'title',
                'title': [
                    {'plain_text': text.get('plain_text', ''), 'href': text.get('href')}
                    for text in instance.get('title', [])
                ]
            }
        elif property_type == 'rich_text':
            return {
                'type': 'rich_text',
                'rich_text': [
                    {'plain_text': text.get('plain_text', ''), 'href': text.get('href')}
                    for text in instance.get('rich_text', [])
                ]
            }
        elif property_type == 'number':
            return {
                'type': 'number',
                'number': instance.get('number')
            }
        elif property_type == 'select':
            select_value = instance.get('select')
            return {
                'type': 'select',
                'select': {
                    'name': select_value.get('name') if select_value else None,
                    'color': select_value.get('color') if select_value else None
                }
            }
        elif property_type == 'multi_select':
            return {
                'type': 'multi_select',
                'multi_select': [
                    {'name': item.get('name'), 'color': item.get('color')}
                    for item in instance.get('multi_select', [])
                ]
            }
        elif property_type == 'date':
            date_value = instance.get('date')
            return {
                'type': 'date',
                'date': {
                    'start': date_value.get('start') if date_value else None,
                    'end': date_value.get('end') if date_value else None
                }
            }
        elif property_type == 'checkbox':
            return {
                'type': 'checkbox',
                'checkbox': instance.get('checkbox', False)
            }
        elif property_type == 'url':
            return {
                'type': 'url',
                'url': instance.get('url')
            }
        elif property_type == 'email':
            return {
                'type': 'email',
                'email': instance.get('email')
            }
        elif property_type == 'phone_number':
            return {
                'type': 'phone_number',
                'phone_number': instance.get('phone_number')
            }
        elif property_type == 'status':
            status_value = instance.get('status')
            return {
                'type': 'status',
                'status': {
                    'name': status_value.get('name') if status_value else None,
                    'color': status_value.get('color') if status_value else None
                }
            }
        else:
            # 알려지지 않은 타입은 원본 그대로 반환
            return instance


class NotionDatabaseSchemaSerializer(serializers.Serializer):
    """Notion 데이터베이스 스키마 직렬화"""
    
    def to_representation(self, instance):
        """스키마를 PWA에서 사용하기 쉬운 형태로 변환"""
        if not isinstance(instance, dict):
            return instance
        
        properties = instance.get('properties', {})
        formatted_properties = {}
        
        for prop_name, prop_config in properties.items():
            formatted_properties[prop_name] = {
                'name': prop_name,
                'type': prop_config.get('type'),
                'id': prop_config.get('id'),
                'description': prop_config.get('description', ''),
                'required': False,  # Notion은 기본적으로 필수 필드 개념이 없음
                'options': self._get_property_options(prop_config)
            }
        
        return {
            'properties': formatted_properties,
            'property_count': len(formatted_properties),
            'title': instance.get('title', []),
            'description': instance.get('description', [])
        }
    
    def _get_property_options(self, prop_config):
        """속성 타입별 옵션 추출"""
        prop_type = prop_config.get('type')
        
        if prop_type == 'select':
            return {
                'options': [
                    {'name': opt.get('name'), 'color': opt.get('color')}
                    for opt in prop_config.get('select', {}).get('options', [])
                ]
            }
        elif prop_type == 'multi_select':
            return {
                'options': [
                    {'name': opt.get('name'), 'color': opt.get('color')}
                    for opt in prop_config.get('multi_select', {}).get('options', [])
                ]
            }
        elif prop_type == 'status':
            return {
                'options': [
                    {'name': opt.get('name'), 'color': opt.get('color')}
                    for opt in prop_config.get('status', {}).get('options', [])
                ]
            }
        elif prop_type == 'number':
            number_config = prop_config.get('number', {})
            return {
                'format': number_config.get('format', 'number')
            }
        elif prop_type in ['formula', 'rollup']:
            return {
                'computed': True,
                'expression': prop_config.get(prop_type, {}).get('expression', '')
            }
        else:
            return {}


class NotionDatabaseCreateSerializer(serializers.Serializer):
    """Notion 데이터베이스 생성 요청"""
    
    notion_id = serializers.CharField(max_length=36, help_text="Notion 데이터베이스 ID")
    title = serializers.CharField(max_length=255, required=False, help_text="데이터베이스 제목")
    description = serializers.CharField(required=False, allow_blank=True, help_text="설명")
    database_type = serializers.ChoiceField(
        choices=NotionDatabase.DatabaseType.choices,
        default=NotionDatabase.DatabaseType.CUSTOM
    )
    sync_interval = serializers.IntegerField(min_value=60, default=300, help_text="동기화 간격(초)")
    
    def validate_notion_id(self, value):
        """중복 확인"""
        if NotionDatabase.objects.filter(notion_id=value, is_active=True).exists():
            raise serializers.ValidationError("이미 등록된 데이터베이스입니다.")
        return value