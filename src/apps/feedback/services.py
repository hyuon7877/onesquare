"""
피드백 시스템 서비스
Notion API 연동 및 비즈니스 로직 처리
"""

from django.conf import settings
from django.db import models
from notion_client import Client
from notion_client.errors import APIResponseError
import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class NotionFeedbackService:
    """Notion API 연동 피드백 서비스"""
    
    def __init__(self):
        self.client = Client(auth=settings.NOTION_TOKEN)
        self.database_id = settings.NOTION_DATABASE_ID
    
    def create_feedback_thread(self, thread) -> Optional[str]:
        """Notion에 피드백 스레드 페이지 생성"""
        try:
            # 피드백 스레드 페이지 속성
            properties = {
                "제목": {
                    "title": [
                        {
                            "text": {
                                "content": f"[피드백] {thread.title}"
                            }
                        }
                    ]
                },
                "유형": {
                    "select": {
                        "name": self._get_thread_type_korean(thread.thread_type)
                    }
                },
                "상태": {
                    "select": {
                        "name": self._get_status_korean(thread.status)
                    }
                },
                "생성자": {
                    "rich_text": [
                        {
                            "text": {
                                "content": thread.creator.get_full_name() or thread.creator.username
                            }
                        }
                    ]
                },
                "생성일시": {
                    "date": {
                        "start": thread.created_at.strftime("%Y-%m-%d")
                    }
                }
            }
            
            # 참여자 정보 추가
            participants = thread.participants.all()
            if participants:
                participant_names = [p.get_full_name() or p.username for p in participants]
                properties["참여자"] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": ", ".join(participant_names)
                            }
                        }
                    ]
                }
            
            # Notion 페이지 생성
            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties,
                children=[
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": "피드백 스레드 정보"
                                    }
                                }
                            ]
                        }
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": f"스레드 ID: {thread.id}\n"
                                                  f"유형: {thread.get_thread_type_display()}\n"
                                                  f"상태: {thread.get_status_display()}\n"
                                                  f"생성자: {thread.creator.get_full_name()}\n"
                                                  f"생성일시: {thread.created_at.strftime('%Y-%m-%d %H:%M')}"
                                    }
                                }
                            ]
                        }
                    },
                    {
                        "object": "block",
                        "type": "divider",
                        "divider": {}
                    }
                ]
            )
            
            return response["id"]
            
        except APIResponseError as e:
            logger.error(f"Notion 피드백 스레드 생성 실패: {e}")
            return None
        except Exception as e:
            logger.error(f"예상치 못한 오류: {e}")
            return None
    
    def sync_message(self, message) -> bool:
        """Notion에 피드백 메시지 동기화"""
        if not message.thread.notion_page_id:
            logger.warning(f"스레드 {message.thread.id}에 Notion 페이지 ID가 없습니다.")
            return False
        
        try:
            # 메시지 블록 생성
            blocks = []
            
            # 메시지 헤더
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": f"{message.sender.get_full_name()} - {message.created_at.strftime('%Y-%m-%d %H:%M')}"
                            }
                        }
                    ]
                }
            })
            
            # 메시지 내용
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": message.content
                            }
                        }
                    ]
                }
            })
            
            # 첨부파일 정보 추가
            attachments = message.get_attachments()
            if attachments:
                attachment_info = []
                for attachment in attachments:
                    attachment_info.append(
                        f"📎 {attachment.original_filename} ({attachment.formatted_file_size})"
                    )
                
                blocks.append({
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "첨부파일:\n" + "\n".join(attachment_info)
                                }
                            }
                        ],
                        "icon": {
                            "emoji": "📎"
                        }
                    }
                })
            
            # 회신 메시지인 경우 표시
            if message.parent_message:
                blocks.insert(1, {
                    "object": "block",
                    "type": "quote",
                    "quote": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"↳ {message.parent_message.sender.get_full_name()}님의 메시지에 대한 회신"
                                }
                            }
                        ]
                    }
                })
            
            # 구분선
            blocks.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })
            
            # Notion 페이지에 블록 추가
            self.client.blocks.children.append(
                block_id=message.thread.notion_page_id,
                children=blocks
            )
            
            # 동기화 완료 표시
            message.notion_synced = True
            message.save()
            
            return True
            
        except APIResponseError as e:
            logger.error(f"Notion 메시지 동기화 실패: {e}")
            return False
        except Exception as e:
            logger.error(f"예상치 못한 오류: {e}")
            return False
    
    def update_thread_status(self, thread, status) -> bool:
        """Notion에서 스레드 상태 업데이트"""
        if not thread.notion_page_id:
            return False
        
        try:
            self.client.pages.update(
                page_id=thread.notion_page_id,
                properties={
                    "상태": {
                        "select": {
                            "name": self._get_status_korean(status)
                        }
                    },
                    "수정일시": {
                        "date": {
                            "start": datetime.now().strftime("%Y-%m-%d")
                        }
                    }
                }
            )
            return True
            
        except APIResponseError as e:
            logger.error(f"Notion 상태 업데이트 실패: {e}")
            return False
    
    def _get_thread_type_korean(self, thread_type: str) -> str:
        """스레드 유형을 한국어로 변환"""
        type_map = {
            'task_feedback': '업무 피드백',
            'report_feedback': '보고서 피드백',
            'general_feedback': '일반 피드백',
            'urgent_feedback': '긴급 피드백',
        }
        return type_map.get(thread_type, thread_type)
    
    def _get_status_korean(self, status: str) -> str:
        """상태를 한국어로 변환"""
        status_map = {
            'active': '활성',
            'resolved': '해결됨',
            'closed': '종료됨',
            'archived': '보관됨',
        }
        return status_map.get(status, status)


class FeedbackStatisticsService:
    """피드백 시스템 통계 서비스"""
    
    def __init__(self, user=None):
        self.user = user
    
    def get_thread_statistics(self) -> Dict[str, Any]:
        """스레드 통계 정보"""
        from .models import FeedbackThread, FeedbackMessage
        
        stats = {}
        
        # 기본 쿼리셋
        threads_qs = FeedbackThread.objects.all()
        if self.user:
            threads_qs = threads_qs.filter(participants=self.user)
        
        # 스레드 상태별 통계
        stats['thread_counts'] = {
            'total': threads_qs.count(),
            'active': threads_qs.filter(status='active').count(),
            'resolved': threads_qs.filter(status='resolved').count(),
            'closed': threads_qs.filter(status='closed').count(),
        }
        
        # 스레드 유형별 통계
        stats['thread_types'] = {}
        for thread_type, display_name in FeedbackThread.THREAD_TYPES:
            stats['thread_types'][thread_type] = {
                'name': display_name,
                'count': threads_qs.filter(thread_type=thread_type).count()
            }
        
        # 메시지 통계
        messages_qs = FeedbackMessage.objects.filter(thread__in=threads_qs)
        stats['message_counts'] = {
            'total': messages_qs.count(),
            'unread': messages_qs.filter(is_read=False).count() if self.user else 0,
            'with_attachments': messages_qs.filter(attachments__isnull=False).distinct().count(),
        }
        
        return stats
    
    def get_user_activity_stats(self) -> Dict[str, Any]:
        """사용자 활동 통계"""
        if not self.user:
            return {}
        
        from .models import FeedbackThread, FeedbackMessage, FeedbackNotification
        
        stats = {}
        
        # 생성한 스레드 수
        stats['threads_created'] = FeedbackThread.objects.filter(creator=self.user).count()
        
        # 참여한 스레드 수
        stats['threads_participated'] = FeedbackThread.objects.filter(participants=self.user).count()
        
        # 보낸 메시지 수
        stats['messages_sent'] = FeedbackMessage.objects.filter(sender=self.user).count()
        
        # 읽지 않은 알림 수
        stats['unread_notifications'] = FeedbackNotification.objects.filter(
            recipient=self.user,
            is_read=False
        ).count()
        
        return stats
    
    def get_recent_activity(self, days: int = 7) -> Dict[str, Any]:
        """최근 활동 내역"""
        from django.utils import timezone
        from datetime import timedelta
        from .models import FeedbackThread, FeedbackMessage
        
        since_date = timezone.now() - timedelta(days=days)
        
        activity = {}
        
        # 기본 쿼리셋
        threads_qs = FeedbackThread.objects.all()
        if self.user:
            threads_qs = threads_qs.filter(participants=self.user)
        
        # 최근 생성된 스레드
        activity['recent_threads'] = threads_qs.filter(
            created_at__gte=since_date
        ).order_by('-created_at')[:5]
        
        # 최근 메시지
        activity['recent_messages'] = FeedbackMessage.objects.filter(
            thread__in=threads_qs,
            created_at__gte=since_date
        ).select_related('sender', 'thread').order_by('-created_at')[:10]
        
        return activity


class FeedbackFileService:
    """피드백 파일 관리 서비스"""
    
    @staticmethod
    def get_file_type_stats() -> Dict[str, Any]:
        """파일 유형별 통계"""
        from .models import MediaAttachment
        
        stats = {}
        
        # 미디어 유형별 통계
        for media_type, display_name in MediaAttachment.MEDIA_TYPES:
            count = MediaAttachment.objects.filter(media_type=media_type).count()
            total_size = MediaAttachment.objects.filter(
                media_type=media_type
            ).aggregate(
                total_size=models.Sum('file_size')
            )['total_size'] or 0
            
            stats[media_type] = {
                'name': display_name,
                'count': count,
                'total_size': total_size,
                'formatted_size': FeedbackFileService.format_file_size(total_size)
            }
        
        return stats
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """파일 크기를 사람이 읽기 쉬운 형태로 변환"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"
    
    @staticmethod
    def cleanup_orphaned_files():
        """고아 파일 정리 (메시지가 삭제된 첨부파일)"""
        from .models import MediaAttachment
        import os
        
        # 실제로는 메시지가 삭제되어도 첨부파일은 CASCADE로 자동 삭제되므로
        # 파일 시스템에서 남은 파일들을 정리하는 로직
        
        attachments = MediaAttachment.objects.all()
        cleaned_count = 0
        
        for attachment in attachments:
            if attachment.file and not os.path.exists(attachment.file.path):
                # 파일이 실제로 존재하지 않으면 DB 레코드 삭제
                attachment.delete()
                cleaned_count += 1
        
        return cleaned_count