"""
피드백 시스템 시리얼라이저
DRF용 JSON 직렬화 및 역직렬화 클래스
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    FeedbackThread,
    ThreadParticipant,
    FeedbackMessage,
    MediaAttachment,
    FeedbackNotification
)

User = get_user_model()


class MediaAttachmentSerializer(serializers.ModelSerializer):
    """미디어 첨부파일 시리얼라이저"""
    formatted_file_size = serializers.ReadOnlyField()
    is_image = serializers.ReadOnlyField()
    is_video = serializers.ReadOnlyField()
    
    class Meta:
        model = MediaAttachment
        fields = [
            'id', 'file', 'original_filename', 'media_type',
            'file_size', 'formatted_file_size', 'width', 'height',
            'duration', 'is_compressed', 'compression_level',
            'original_size', 'thumbnail', 'is_image', 'is_video',
            'created_at'
        ]
        read_only_fields = ['id', 'media_type', 'file_size', 'width', 'height', 'created_at']

    def create(self, validated_data):
        """첨부파일 생성"""
        # 원본 파일명 자동 설정
        if 'file' in validated_data and not validated_data.get('original_filename'):
            validated_data['original_filename'] = validated_data['file'].name
        
        return super().create(validated_data)


class FeedbackMessageSerializer(serializers.ModelSerializer):
    """피드백 메시지 시리얼라이저"""
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    sender_username = serializers.CharField(source='sender.username', read_only=True)
    reply_count = serializers.ReadOnlyField()
    attachments = MediaAttachmentSerializer(many=True, read_only=True)
    
    # 스레드형 댓글용 회신 메시지
    replies = serializers.SerializerMethodField()
    
    class Meta:
        model = FeedbackMessage
        fields = [
            'id', 'thread', 'sender', 'sender_name', 'sender_username',
            'message_type', 'content', 'parent_message',
            'is_read', 'is_edited', 'is_system', 'notion_synced',
            'reply_count', 'attachments', 'replies',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'sender', 'is_edited', 'notion_synced', 'created_at', 'updated_at']

    def get_replies(self, obj):
        """회신 메시지 목록 (재귀적으로 가져오지 않음 - 성능상 이유)"""
        # 직접적인 회신만 가져오기 (depth 1)
        replies = obj.replies.all()[:5]  # 최대 5개만
        return FeedbackMessageSerializer(replies, many=True, context=self.context).data

    def validate_content(self, value):
        """메시지 내용 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError("메시지 내용은 필수입니다.")
        
        if len(value) > 5000:
            raise serializers.ValidationError("메시지는 5000자를 초과할 수 없습니다.")
        
        return value.strip()


class ThreadParticipantSerializer(serializers.ModelSerializer):
    """스레드 참여자 시리얼라이저"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = ThreadParticipant
        fields = [
            'user', 'user_name', 'user_username', 'user_email',
            'role', 'joined_at', 'is_active'
        ]
        read_only_fields = ['joined_at']


class FeedbackThreadListSerializer(serializers.ModelSerializer):
    """피드백 스레드 목록용 시리얼라이저 (요약 정보)"""
    creator_name = serializers.CharField(source='creator.get_full_name', read_only=True)
    participant_count = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()
    unread_count = serializers.ReadOnlyField()
    latest_message = serializers.SerializerMethodField()
    
    class Meta:
        model = FeedbackThread
        fields = [
            'id', 'title', 'thread_type', 'status',
            'creator', 'creator_name', 'participant_count', 'message_count',
            'unread_count', 'latest_message',
            'created_at', 'updated_at', 'last_activity'
        ]

    def get_participant_count(self, obj):
        """참여자 수"""
        return obj.participants.filter(threadparticipant__is_active=True).count()

    def get_message_count(self, obj):
        """메시지 수"""
        return obj.messages.count()

    def get_latest_message(self, obj):
        """최신 메시지 요약"""
        latest = obj.get_latest_message()
        if latest:
            return {
                'id': str(latest.id),
                'content': latest.content[:100] + '...' if len(latest.content) > 100 else latest.content,
                'sender_name': latest.sender.get_full_name(),
                'created_at': latest.created_at,
                'message_type': latest.message_type
            }
        return None


class FeedbackThreadDetailSerializer(serializers.ModelSerializer):
    """피드백 스레드 상세용 시리얼라이저"""
    creator_name = serializers.CharField(source='creator.get_full_name', read_only=True)
    participants_detail = ThreadParticipantSerializer(source='threadparticipant_set', many=True, read_only=True)
    messages = FeedbackMessageSerializer(many=True, read_only=True)
    unread_count = serializers.ReadOnlyField()
    
    # 생성할 때 참여자 추가용
    participant_usernames = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        help_text="참여자 사용자명 목록"
    )
    
    class Meta:
        model = FeedbackThread
        fields = [
            'id', 'title', 'thread_type', 'status',
            'creator', 'creator_name', 'participants_detail',
            'participant_usernames', 'notion_page_id', 'unread_count',
            'messages', 'created_at', 'updated_at', 'last_activity'
        ]
        read_only_fields = ['id', 'creator', 'created_at', 'updated_at', 'last_activity']

    def create(self, validated_data):
        """스레드 생성"""
        participant_usernames = validated_data.pop('participant_usernames', [])
        
        # 현재 사용자를 생성자로 설정
        validated_data['creator'] = self.context['request'].user
        
        thread = super().create(validated_data)
        
        # 생성자를 관리자로 추가
        ThreadParticipant.objects.create(
            thread=thread,
            user=thread.creator,
            role='admin'
        )
        
        # 다른 참여자들 추가
        for username in participant_usernames:
            try:
                user = User.objects.get(username=username)
                ThreadParticipant.objects.get_or_create(
                    thread=thread,
                    user=user,
                    defaults={'role': 'partner'}
                )
            except User.DoesNotExist:
                continue  # 존재하지 않는 사용자는 무시
        
        return thread

    def validate_title(self, value):
        """제목 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError("스레드 제목은 필수입니다.")
        
        if len(value) > 200:
            raise serializers.ValidationError("제목은 200자를 초과할 수 없습니다.")
        
        return value.strip()


class FeedbackNotificationSerializer(serializers.ModelSerializer):
    """피드백 알림 시리얼라이저"""
    thread_title = serializers.CharField(source='thread.title', read_only=True)
    
    class Meta:
        model = FeedbackNotification
        fields = [
            'id', 'recipient', 'thread', 'thread_title', 'message',
            'notification_type', 'title', 'content',
            'is_read', 'created_at'
        ]
        read_only_fields = ['id', 'recipient', 'created_at']


# 파일 업로드용 특별 시리얼라이저
class FileUploadSerializer(serializers.Serializer):
    """멀티미디어 파일 업로드용 시리얼라이저"""
    files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=False,
        help_text="업로드할 파일 목록"
    )
    message_id = serializers.UUIDField(
        help_text="첨부할 메시지 ID"
    )
    compression_level = serializers.ChoiceField(
        choices=MediaAttachment.COMPRESSION_LEVELS,
        default='medium',
        help_text="이미지 압축 레벨"
    )

    def validate_files(self, value):
        """파일 검증"""
        max_file_size = 50 * 1024 * 1024  # 50MB
        max_files = 10
        
        if len(value) > max_files:
            raise serializers.ValidationError(f"최대 {max_files}개 파일만 업로드할 수 있습니다.")
        
        for file_obj in value:
            if file_obj.size > max_file_size:
                raise serializers.ValidationError(f"파일 크기는 50MB를 초과할 수 없습니다: {file_obj.name}")
        
        return value

    def validate_message_id(self, value):
        """메시지 존재 확인"""
        try:
            message = FeedbackMessage.objects.get(id=value)
            return value
        except FeedbackMessage.DoesNotExist:
            raise serializers.ValidationError("존재하지 않는 메시지입니다.")


# 스레드 검색용 시리얼라이저
class ThreadSearchSerializer(serializers.Serializer):
    """스레드 검색용 시리얼라이저"""
    query = serializers.CharField(
        required=False,
        help_text="검색어 (제목, 내용)"
    )
    thread_type = serializers.ChoiceField(
        choices=FeedbackThread.THREAD_TYPES,
        required=False,
        help_text="피드백 유형 필터"
    )
    status = serializers.ChoiceField(
        choices=FeedbackThread.STATUS_CHOICES,
        required=False,
        help_text="상태 필터"
    )
    date_from = serializers.DateTimeField(
        required=False,
        help_text="시작 날짜"
    )
    date_to = serializers.DateTimeField(
        required=False,
        help_text="종료 날짜"
    )
    creator = serializers.CharField(
        required=False,
        help_text="생성자 사용자명"
    )
    participant = serializers.CharField(
        required=False,
        help_text="참여자 사용자명"
    )

    def validate(self, data):
        """전체 데이터 검증"""
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError("시작 날짜는 종료 날짜보다 늦을 수 없습니다.")
        
        return data


# 메시지 검색용 시리얼라이저
class MessageSearchSerializer(serializers.Serializer):
    """메시지 검색용 시리얼라이저"""
    query = serializers.CharField(
        required=True,
        help_text="검색어"
    )
    thread_id = serializers.UUIDField(
        required=False,
        help_text="특정 스레드 내에서만 검색"
    )
    message_type = serializers.ChoiceField(
        choices=FeedbackMessage.MESSAGE_TYPES,
        required=False,
        help_text="메시지 유형 필터"
    )
    sender = serializers.CharField(
        required=False,
        help_text="발신자 사용자명"
    )
    date_from = serializers.DateTimeField(
        required=False,
        help_text="시작 날짜"
    )
    date_to = serializers.DateTimeField(
        required=False,
        help_text="종료 날짜"
    )

    def validate_query(self, value):
        """검색어 검증"""
        if len(value.strip()) < 2:
            raise serializers.ValidationError("검색어는 최소 2자 이상이어야 합니다.")
        
        return value.strip()