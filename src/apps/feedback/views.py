"""
멀티미디어 피드백 시스템 뷰
파트너-관리자 간 양방향 피드백 API 뷰
"""

from django.shortcuts import render, get_object_or_404
from django.db import transaction
from django.db.models import Q, Prefetch
from django.contrib.auth import get_user_model
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
import uuid

from .models import (
    FeedbackThread,
    ThreadParticipant,
    FeedbackMessage,
    MediaAttachment,
    FeedbackNotification
)
from .serializers import (
    FeedbackThreadListSerializer,
    FeedbackThreadDetailSerializer,
    FeedbackMessageSerializer,
    MediaAttachmentSerializer,
    FeedbackNotificationSerializer,
    FileUploadSerializer,
    ThreadSearchSerializer,
    MessageSearchSerializer
)
from .services import NotionFeedbackService

User = get_user_model()


class FeedbackThreadViewSet(viewsets.ModelViewSet):
    """피드백 스레드 ViewSet"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        """액션에 따른 시리얼라이저 선택"""
        if self.action == 'list':
            return FeedbackThreadListSerializer
        return FeedbackThreadDetailSerializer
    
    def get_queryset(self):
        """사용자가 참여한 스레드만 반환"""
        user = self.request.user
        return FeedbackThread.objects.filter(
            participants=user
        ).select_related('creator').prefetch_related(
            'participants',
            'messages__sender',
            'messages__attachments'
        ).distinct()
    
    def perform_create(self, serializer):
        """스레드 생성"""
        thread = serializer.save()
        
        # Notion 동기화
        try:
            notion_service = NotionFeedbackService()
            notion_page_id = notion_service.create_feedback_thread(thread)
            if notion_page_id:
                thread.notion_page_id = notion_page_id
                thread.save()
        except Exception as e:
            # Notion 동기화 실패는 로그만 남기고 진행
            print(f"Notion 동기화 실패: {e}")
        
        # 참여자들에게 알림
        self._send_thread_notification(
            thread, 
            'thread_created',
            f"새로운 피드백 스레드가 생성되었습니다: {thread.title}"
        )
    
    def _send_thread_notification(self, thread, notification_type, content):
        """스레드 관련 알림 발송"""
        participants = thread.participants.exclude(id=thread.creator.id)
        notifications = []
        
        for participant in participants:
            notifications.append(FeedbackNotification(
                recipient=participant,
                thread=thread,
                notification_type=notification_type,
                title=f"피드백 스레드: {thread.title}",
                content=content
            ))
        
        FeedbackNotification.objects.bulk_create(notifications)
    
    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        """참여자 추가"""
        thread = self.get_object()
        username = request.data.get('username')
        role = request.data.get('role', 'partner')
        
        if not username:
            return Response(
                {'error': '사용자명이 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response(
                {'error': '사용자를 찾을 수 없습니다.'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        participant, created = ThreadParticipant.objects.get_or_create(
            thread=thread,
            user=user,
            defaults={'role': role}
        )
        
        if not created:
            return Response(
                {'error': '이미 참여 중인 사용자입니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 알림 발송
        FeedbackNotification.objects.create(
            recipient=user,
            thread=thread,
            notification_type='assignment',
            title=f"피드백 스레드에 초대되었습니다",
            content=f"{thread.creator.get_full_name()}님이 '{thread.title}' 스레드에 초대했습니다."
        )
        
        return Response({'message': '참여자가 추가되었습니다.'})
    
    @action(detail=True, methods=['post'])
    def remove_participant(self, request, pk=None):
        """참여자 제거"""
        thread = self.get_object()
        username = request.data.get('username')
        
        if not username:
            return Response(
                {'error': '사용자명이 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            participant = ThreadParticipant.objects.get(
                thread=thread,
                user__username=username
            )
            participant.delete()
            return Response({'message': '참여자가 제거되었습니다.'})
        except ThreadParticipant.DoesNotExist:
            return Response(
                {'error': '참여자를 찾을 수 없습니다.'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def mark_resolved(self, request, pk=None):
        """스레드 해결됨으로 표시"""
        thread = self.get_object()
        thread.status = 'resolved'
        thread.save()
        
        # Notion 동기화
        try:
            notion_service = NotionFeedbackService()
            notion_service.update_thread_status(thread, 'resolved')
        except Exception as e:
            print(f"Notion 상태 업데이트 실패: {e}")
        
        # 알림 발송
        self._send_thread_notification(
            thread,
            'thread_resolved',
            f"피드백 스레드가 해결되었습니다: {thread.title}"
        )
        
        return Response({'message': '스레드가 해결됨으로 표시되었습니다.'})
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """스레드 읽음 표시"""
        thread = self.get_object()
        thread.mark_as_read(request.user)
        return Response({'message': '읽음으로 표시되었습니다.'})
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """스레드 검색"""
        search_serializer = ThreadSearchSerializer(data=request.GET)
        search_serializer.is_valid(raise_exception=True)
        
        data = search_serializer.validated_data
        queryset = self.get_queryset()
        
        # 검색어 필터
        if data.get('query'):
            queryset = queryset.filter(
                Q(title__icontains=data['query']) |
                Q(messages__content__icontains=data['query'])
            ).distinct()
        
        # 기타 필터들
        if data.get('thread_type'):
            queryset = queryset.filter(thread_type=data['thread_type'])
        
        if data.get('status'):
            queryset = queryset.filter(status=data['status'])
        
        if data.get('date_from'):
            queryset = queryset.filter(created_at__gte=data['date_from'])
        
        if data.get('date_to'):
            queryset = queryset.filter(created_at__lte=data['date_to'])
        
        if data.get('creator'):
            queryset = queryset.filter(creator__username=data['creator'])
        
        if data.get('participant'):
            queryset = queryset.filter(participants__username=data['participant'])
        
        # 페이지네이션 및 직렬화
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = FeedbackThreadListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = FeedbackThreadListSerializer(queryset, many=True)
        return Response(serializer.data)


class FeedbackMessageViewSet(viewsets.ModelViewSet):
    """피드백 메시지 ViewSet"""
    serializer_class = FeedbackMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """사용자가 참여한 스레드의 메시지만 반환"""
        user = self.request.user
        return FeedbackMessage.objects.filter(
            thread__participants=user
        ).select_related(
            'sender',
            'thread'
        ).prefetch_related(
            'attachments',
            'replies__sender'
        ).distinct()
    
    def perform_create(self, serializer):
        """메시지 생성"""
        message = serializer.save(sender=self.request.user)
        
        # 스레드 마지막 활동 시간 업데이트
        message.thread.last_activity = timezone.now()
        message.thread.save()
        
        # Notion 동기화
        try:
            notion_service = NotionFeedbackService()
            notion_service.sync_message(message)
        except Exception as e:
            print(f"Notion 메시지 동기화 실패: {e}")
        
        # 다른 참여자들에게 알림
        participants = message.thread.participants.exclude(id=message.sender.id)
        notifications = []
        
        for participant in participants:
            notifications.append(FeedbackNotification(
                recipient=participant,
                thread=message.thread,
                message=message,
                notification_type='new_message',
                title=f"새 메시지: {message.thread.title}",
                content=f"{message.sender.get_full_name()}: {message.content[:100]}"
            ))
        
        FeedbackNotification.objects.bulk_create(notifications)
    
    @action(detail=True, methods=['post'])
    def reply(self, request, pk=None):
        """메시지에 회신"""
        parent_message = self.get_object()
        content = request.data.get('content', '').strip()
        
        if not content:
            return Response(
                {'error': '메시지 내용이 필요합니다.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reply = FeedbackMessage.objects.create(
            thread=parent_message.thread,
            sender=request.user,
            content=content,
            parent_message=parent_message,
            message_type='text'
        )
        
        # 스레드 활동 시간 업데이트
        parent_message.thread.last_activity = timezone.now()
        parent_message.thread.save()
        
        serializer = FeedbackMessageSerializer(reply)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """메시지 읽음 표시"""
        message = self.get_object()
        message.is_read = True
        message.save()
        return Response({'message': '읽음으로 표시되었습니다.'})
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """메시지 검색"""
        search_serializer = MessageSearchSerializer(data=request.GET)
        search_serializer.is_valid(raise_exception=True)
        
        data = search_serializer.validated_data
        queryset = self.get_queryset()
        
        # 검색어 필터 (필수)
        queryset = queryset.filter(content__icontains=data['query'])
        
        # 기타 필터들
        if data.get('thread_id'):
            queryset = queryset.filter(thread_id=data['thread_id'])
        
        if data.get('message_type'):
            queryset = queryset.filter(message_type=data['message_type'])
        
        if data.get('sender'):
            queryset = queryset.filter(sender__username=data['sender'])
        
        if data.get('date_from'):
            queryset = queryset.filter(created_at__gte=data['date_from'])
        
        if data.get('date_to'):
            queryset = queryset.filter(created_at__lte=data['date_to'])
        
        # 페이지네이션
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = FeedbackMessageSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = FeedbackMessageSerializer(queryset, many=True)
        return Response(serializer.data)


class MediaAttachmentViewSet(viewsets.ModelViewSet):
    """미디어 첨부파일 ViewSet"""
    serializer_class = MediaAttachmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        """사용자가 참여한 스레드의 첨부파일만 반환"""
        user = self.request.user
        return MediaAttachment.objects.filter(
            message__thread__participants=user
        ).select_related('message__thread', 'message__sender').distinct()
    
    @action(detail=False, methods=['post'])
    def upload_multiple(self, request):
        """다중 파일 업로드"""
        upload_serializer = FileUploadSerializer(data=request.data)
        upload_serializer.is_valid(raise_exception=True)
        
        files = upload_serializer.validated_data['files']
        message_id = upload_serializer.validated_data['message_id']
        compression_level = upload_serializer.validated_data['compression_level']
        
        try:
            message = FeedbackMessage.objects.get(
                id=message_id,
                thread__participants=request.user
            )
        except FeedbackMessage.DoesNotExist:
            return Response(
                {'error': '메시지를 찾을 수 없거나 접근 권한이 없습니다.'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        attachments = []
        
        with transaction.atomic():
            for file_obj in files:
                attachment = MediaAttachment.objects.create(
                    message=message,
                    file=file_obj,
                    original_filename=file_obj.name,
                    compression_level=compression_level
                )
                attachments.append(attachment)
        
        # 메시지 유형 업데이트 (첨부파일이 있으면)
        if attachments:
            # 주로 이미지인지 확인
            image_count = sum(1 for att in attachments if att.is_image)
            if image_count > 0:
                message.message_type = 'image'
            else:
                message.message_type = 'file'
            message.save()
        
        serializer = MediaAttachmentSerializer(attachments, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FeedbackNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """피드백 알림 ViewSet (읽기 전용)"""
    serializer_class = FeedbackNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """현재 사용자의 알림만 반환"""
        return FeedbackNotification.objects.filter(
            recipient=self.request.user
        ).select_related('thread', 'message').order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """알림 읽음 표시"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'message': '읽음으로 표시되었습니다.'})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """모든 알림 읽음 표시"""
        count = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'message': f'{count}개 알림이 읽음으로 표시되었습니다.'})
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """읽지 않은 알림 수"""
        count = self.get_queryset().filter(is_read=False).count()
        return Response({'unread_count': count})


# PWA 템플릿 뷰
def feedback_dashboard(request):
    """피드백 대시보드 PWA 페이지"""
    return render(request, 'feedback/dashboard.html', {
        'page_title': '피드백 시스템',
        'app_name': 'feedback'
    })


def thread_detail(request, thread_id):
    """피드백 스레드 상세 PWA 페이지"""
    thread = get_object_or_404(FeedbackThread, id=thread_id, participants=request.user)
    return render(request, 'feedback/thread_detail.html', {
        'thread': thread,
        'page_title': f'피드백: {thread.title}',
        'app_name': 'feedback'
    })


def create_thread(request):
    """피드백 스레드 생성 PWA 페이지"""
    return render(request, 'feedback/create_thread.html', {
        'page_title': '새 피드백 스레드',
        'app_name': 'feedback'
    })
