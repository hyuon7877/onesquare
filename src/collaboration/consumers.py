import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from .models import Comment, Notification, Activity, Presence
from asgiref.sync import sync_to_async
import datetime


class CommentConsumer(AsyncWebsocketConsumer):
    """실시간 댓글 업데이트를 위한 WebSocket 컨슈머"""
    
    async def connect(self):
        self.content_type = self.scope['url_route']['kwargs']['content_type']
        self.object_id = self.scope['url_route']['kwargs']['object_id']
        self.room_name = f'comments_{self.content_type}_{self.object_id}'
        self.room_group_name = f'comment_{self.room_name}'
        
        # 룸 그룹에 참여
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # 현재 댓글 목록 전송
        comments = await self.get_comments()
        await self.send(text_data=json.dumps({
            'type': 'initial_comments',
            'comments': comments
        }))
    
    async def disconnect(self, close_code):
        # 룸 그룹에서 나가기
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type')
        
        if message_type == 'new_comment':
            # 새 댓글 생성
            comment = await self.create_comment(text_data_json)
            
            # 룸 그룹에 메시지 전송
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'comment_message',
                    'comment': comment
                }
            )
        
        elif message_type == 'edit_comment':
            # 댓글 수정
            comment = await self.edit_comment(text_data_json)
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'comment_update',
                    'comment': comment
                }
            )
        
        elif message_type == 'delete_comment':
            # 댓글 삭제
            comment_id = text_data_json.get('comment_id')
            await self.delete_comment(comment_id)
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'comment_delete',
                    'comment_id': comment_id
                }
            )
    
    async def comment_message(self, event):
        # WebSocket으로 메시지 전송
        await self.send(text_data=json.dumps({
            'type': 'new_comment',
            'comment': event['comment']
        }))
    
    async def comment_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'comment_updated',
            'comment': event['comment']
        }))
    
    async def comment_delete(self, event):
        await self.send(text_data=json.dumps({
            'type': 'comment_deleted',
            'comment_id': event['comment_id']
        }))
    
    @database_sync_to_async
    def get_comments(self):
        """현재 객체의 모든 댓글 가져오기"""
        try:
            ct = ContentType.objects.get(model=self.content_type)
            comments = Comment.objects.filter(
                content_type=ct,
                object_id=self.object_id
            ).select_related('user').prefetch_related('mentioned_users')
            
            return [self.comment_to_dict(c) for c in comments]
        except ContentType.DoesNotExist:
            return []
    
    @database_sync_to_async
    def create_comment(self, data):
        """새 댓글 생성"""
        user = self.scope['user']
        if not user.is_authenticated:
            return None
        
        ct = ContentType.objects.get(model=self.content_type)
        comment = Comment.objects.create(
            content_type=ct,
            object_id=self.object_id,
            user=user,
            content=data['content'],
            parent_id=data.get('parent_id')
        )
        
        return self.comment_to_dict(comment)
    
    @database_sync_to_async
    def edit_comment(self, data):
        """댓글 수정"""
        user = self.scope['user']
        comment_id = data.get('comment_id')
        
        try:
            comment = Comment.objects.get(id=comment_id, user=user)
            comment.content = data['content']
            comment.is_edited = True
            comment.save()
            return self.comment_to_dict(comment)
        except Comment.DoesNotExist:
            return None
    
    @database_sync_to_async
    def delete_comment(self, comment_id):
        """댓글 삭제"""
        user = self.scope['user']
        try:
            comment = Comment.objects.get(id=comment_id, user=user)
            comment.delete()
            return True
        except Comment.DoesNotExist:
            return False
    
    def comment_to_dict(self, comment):
        """댓글 객체를 딕셔너리로 변환"""
        return {
            'id': comment.id,
            'user': {
                'id': comment.user.id,
                'username': comment.user.username,
                'full_name': comment.user.get_full_name()
            },
            'content': comment.content,
            'created_at': comment.created_at.isoformat(),
            'updated_at': comment.updated_at.isoformat(),
            'is_edited': comment.is_edited,
            'parent_id': comment.parent_id,
            'mentioned_users': [u.username for u in comment.mentioned_users.all()]
        }


class NotificationConsumer(AsyncWebsocketConsumer):
    """실시간 알림 푸시를 위한 WebSocket 컨슈머"""
    
    async def connect(self):
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        self.user_group_name = f'notifications_{self.user.id}'
        
        # 사용자별 알림 그룹에 참여
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # 읽지 않은 알림 전송
        unread_notifications = await self.get_unread_notifications()
        await self.send(text_data=json.dumps({
            'type': 'initial_notifications',
            'notifications': unread_notifications,
            'unread_count': len(unread_notifications)
        }))
    
    async def disconnect(self, close_code):
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type')
        
        if message_type == 'mark_read':
            # 알림을 읽음으로 표시
            notification_id = text_data_json.get('notification_id')
            await self.mark_notification_read(notification_id)
            
        elif message_type == 'mark_all_read':
            # 모든 알림을 읽음으로 표시
            await self.mark_all_notifications_read()
    
    async def notification_message(self, event):
        """새 알림 메시지 전송"""
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'notification': event['notification']
        }))
    
    @database_sync_to_async
    def get_unread_notifications(self):
        """읽지 않은 알림 가져오기"""
        notifications = Notification.objects.filter(
            user=self.user,
            is_read=False
        ).order_by('-created_at')[:20]
        
        return [self.notification_to_dict(n) for n in notifications]
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """알림을 읽음으로 표시"""
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user=self.user
            )
            notification.is_read = True
            notification.save()
            return True
        except Notification.DoesNotExist:
            return False
    
    @database_sync_to_async
    def mark_all_notifications_read(self):
        """모든 알림을 읽음으로 표시"""
        Notification.objects.filter(
            user=self.user,
            is_read=False
        ).update(is_read=True)
    
    def notification_to_dict(self, notification):
        """알림 객체를 딕셔너리로 변환"""
        return {
            'id': notification.id,
            'type': notification.notification_type,
            'message': notification.message,
            'is_read': notification.is_read,
            'created_at': notification.created_at.isoformat(),
            'data': notification.data or {}
        }


class PresenceConsumer(AsyncWebsocketConsumer):
    """온라인 사용자 상태 동기화를 위한 WebSocket 컨슈머"""
    
    async def connect(self):
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            await self.close()
            return
        
        self.presence_group_name = 'presence_all'
        
        # 전체 presence 그룹에 참여
        await self.channel_layer.group_add(
            self.presence_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # 사용자 온라인 상태 업데이트
        await self.update_user_presence(True)
        
        # 현재 온라인 사용자 목록 전송
        online_users = await self.get_online_users()
        await self.send(text_data=json.dumps({
            'type': 'online_users',
            'users': online_users
        }))
        
        # 다른 사용자들에게 온라인 알림
        await self.channel_layer.group_send(
            self.presence_group_name,
            {
                'type': 'user_status_change',
                'user_id': self.user.id,
                'username': self.user.username,
                'status': 'online'
            }
        )
    
    async def disconnect(self, close_code):
        if hasattr(self, 'user'):
            # 사용자 오프라인 상태 업데이트
            await self.update_user_presence(False)
            
            # 다른 사용자들에게 오프라인 알림
            await self.channel_layer.group_send(
                self.presence_group_name,
                {
                    'type': 'user_status_change',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'status': 'offline'
                }
            )
            
            await self.channel_layer.group_discard(
                self.presence_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type')
        
        if message_type == 'heartbeat':
            # 하트비트 - 온라인 상태 유지
            await self.update_user_presence(True)
            await self.send(text_data=json.dumps({
                'type': 'heartbeat_ack'
            }))
        
        elif message_type == 'status_update':
            # 상태 메시지 업데이트
            status_message = text_data_json.get('status_message', '')
            await self.update_status_message(status_message)
            
            await self.channel_layer.group_send(
                self.presence_group_name,
                {
                    'type': 'user_status_update',
                    'user_id': self.user.id,
                    'username': self.user.username,
                    'status_message': status_message
                }
            )
    
    async def user_status_change(self, event):
        """사용자 상태 변경 알림"""
        await self.send(text_data=json.dumps({
            'type': 'user_status_changed',
            'user_id': event['user_id'],
            'username': event['username'],
            'status': event['status']
        }))
    
    async def user_status_update(self, event):
        """사용자 상태 메시지 업데이트"""
        await self.send(text_data=json.dumps({
            'type': 'user_status_updated',
            'user_id': event['user_id'],
            'username': event['username'],
            'status_message': event['status_message']
        }))
    
    @database_sync_to_async
    def update_user_presence(self, is_online):
        """사용자 presence 상태 업데이트"""
        presence, created = Presence.objects.get_or_create(user=self.user)
        presence.is_online = is_online
        presence.last_seen = datetime.datetime.now()
        presence.save()
    
    @database_sync_to_async
    def update_status_message(self, status_message):
        """사용자 상태 메시지 업데이트"""
        presence, created = Presence.objects.get_or_create(user=self.user)
        presence.status_message = status_message
        presence.save()
    
    @database_sync_to_async
    def get_online_users(self):
        """현재 온라인 사용자 목록 가져오기"""
        # 최근 5분 이내 활동한 사용자를 온라인으로 간주
        five_minutes_ago = datetime.datetime.now() - datetime.timedelta(minutes=5)
        online_presences = Presence.objects.filter(
            is_online=True,
            last_seen__gte=five_minutes_ago
        ).select_related('user')
        
        return [
            {
                'id': p.user.id,
                'username': p.user.username,
                'full_name': p.user.get_full_name(),
                'status_message': p.status_message,
                'last_seen': p.last_seen.isoformat()
            }
            for p in online_presences
        ]


class ActivityConsumer(AsyncWebsocketConsumer):
    """실시간 활동 피드를 위한 WebSocket 컨슈머"""
    
    async def connect(self):
        self.user = self.scope['user']
        self.activity_group_name = 'activity_feed'
        
        # 활동 피드 그룹에 참여
        await self.channel_layer.group_add(
            self.activity_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # 최근 활동 전송
        recent_activities = await self.get_recent_activities()
        await self.send(text_data=json.dumps({
            'type': 'initial_activities',
            'activities': recent_activities
        }))
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.activity_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type')
        
        if message_type == 'load_more':
            # 더 많은 활동 로드
            offset = text_data_json.get('offset', 0)
            activities = await self.get_activities(offset)
            
            await self.send(text_data=json.dumps({
                'type': 'more_activities',
                'activities': activities
            }))
    
    async def activity_message(self, event):
        """새 활동 메시지 전송"""
        await self.send(text_data=json.dumps({
            'type': 'new_activity',
            'activity': event['activity']
        }))
    
    @database_sync_to_async
    def get_recent_activities(self):
        """최근 활동 가져오기"""
        activities = Activity.objects.all().select_related('user')[:20]
        return [self.activity_to_dict(a) for a in activities]
    
    @database_sync_to_async
    def get_activities(self, offset=0):
        """활동 페이지네이션"""
        activities = Activity.objects.all().select_related('user')[offset:offset+20]
        return [self.activity_to_dict(a) for a in activities]
    
    def activity_to_dict(self, activity):
        """활동 객체를 딕셔너리로 변환"""
        return {
            'id': activity.id,
            'user': {
                'id': activity.user.id,
                'username': activity.user.username,
                'full_name': activity.user.get_full_name()
            },
            'activity_type': activity.activity_type,
            'description': activity.description,
            'created_at': activity.created_at.isoformat(),
            'metadata': activity.metadata or {}
        }
    
    @classmethod
    async def broadcast_activity(cls, activity_data):
        """모든 연결된 클라이언트에 활동 브로드캐스트"""
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        
        await channel_layer.group_send(
            'activity_feed',
            {
                'type': 'activity_message',
                'activity': activity_data
            }
        )