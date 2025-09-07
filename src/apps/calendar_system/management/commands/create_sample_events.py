"""
샘플 캘린더 이벤트 생성 명령어
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
from apps.calendar_system.models import CalendarEvent, CalendarCategory, EventAttendee
import random

User = get_user_model()


class Command(BaseCommand):
    help = '샘플 캘린더 이벤트를 생성합니다'

    def handle(self, *args, **options):
        # 첫 번째 관리자 사용자 가져오기
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            user = User.objects.first()
            if not user:
                self.stdout.write(self.style.ERROR('사용자가 없습니다. 먼저 사용자를 생성해주세요.'))
                return

        # 카테고리 생성
        categories = []
        category_data = [
            {'name': '회의', 'color': '#667eea', 'description': '팀 미팅 및 회의'},
            {'name': '업무', 'color': '#48bb78', 'description': '일반 업무 일정'},
            {'name': '휴가', 'color': '#ed8936', 'description': '휴가 및 개인 일정'},
            {'name': '교육', 'color': '#38b2ac', 'description': '교육 및 세미나'},
            {'name': '마감', 'color': '#f56565', 'description': '프로젝트 마감일'},
        ]

        for cat_data in category_data:
            category, created = CalendarCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'color': cat_data['color'],
                    'description': cat_data['description'],
                    'is_active': True,
                    'accessible_user_types': ['SUPER_ADMIN', 'MANAGER', 'TEAM_MEMBER']
                }
            )
            categories.append(category)
            if created:
                self.stdout.write(self.style.SUCCESS(f'카테고리 생성: {category.name}'))

        # 샘플 이벤트 생성
        now = timezone.now()
        events_data = [
            # 오늘 일정
            {
                'title': '주간 팀 회의',
                'start': now.replace(hour=10, minute=0),
                'end': now.replace(hour=11, minute=0),
                'category': 0,  # 회의
                'type': 'meeting',
                'priority': 'high',
                'location': '회의실 A',
                'description': '이번 주 진행 상황 공유 및 다음 주 계획 논의'
            },
            {
                'title': '점심 미팅',
                'start': now.replace(hour=12, minute=30),
                'end': now.replace(hour=13, minute=30),
                'category': 0,  # 회의
                'type': 'meeting',
                'priority': 'medium',
                'location': '1층 카페',
                'description': '신규 프로젝트 논의'
            },
            
            # 내일 일정
            {
                'title': 'Q3 실적 보고서 작성',
                'start': (now + timedelta(days=1)).replace(hour=9, minute=0),
                'end': (now + timedelta(days=1)).replace(hour=17, minute=0),
                'category': 1,  # 업무
                'type': 'work',
                'priority': 'high',
                'description': '3분기 실적 보고서 작성 및 검토'
            },
            
            # 이번 주 일정
            {
                'title': 'React 교육 세미나',
                'start': (now + timedelta(days=3)).replace(hour=14, minute=0),
                'end': (now + timedelta(days=3)).replace(hour=18, minute=0),
                'category': 3,  # 교육
                'type': 'work',
                'priority': 'medium',
                'location': '교육실 B1',
                'description': 'React 18 새로운 기능 및 최적화 기법'
            },
            {
                'title': '프로젝트 A 마감',
                'start': (now + timedelta(days=5)).replace(hour=0, minute=0),
                'end': (now + timedelta(days=5)).replace(hour=23, minute=59),
                'category': 4,  # 마감
                'type': 'deadline',
                'priority': 'urgent',
                'is_all_day': True,
                'description': 'OneSquare 프로젝트 1차 마감일'
            },
            
            # 다음 주 일정
            {
                'title': '여름 휴가',
                'start': (now + timedelta(days=10)).replace(hour=0, minute=0),
                'end': (now + timedelta(days=14)).replace(hour=23, minute=59),
                'category': 2,  # 휴가
                'type': 'vacation',
                'priority': 'low',
                'is_all_day': True,
                'description': '연차 휴가'
            },
            {
                'title': '클라이언트 미팅',
                'start': (now + timedelta(days=7)).replace(hour=15, minute=0),
                'end': (now + timedelta(days=7)).replace(hour=16, minute=30),
                'category': 0,  # 회의
                'type': 'meeting',
                'priority': 'high',
                'location': '온라인 (Zoom)',
                'description': '프로젝트 진행 상황 보고 및 피드백 수렴'
            },
            {
                'title': '월간 전체 회의',
                'start': (now + timedelta(days=15)).replace(hour=14, minute=0),
                'end': (now + timedelta(days=15)).replace(hour=16, minute=0),
                'category': 0,  # 회의
                'type': 'meeting',
                'priority': 'medium',
                'location': '대강당',
                'description': '전사 월간 회의 및 공지사항 전달'
            },
            
            # 반복 일정 예시 (매주 월요일)
            {
                'title': '주간 스프린트 계획',
                'start': (now + timedelta(days=(7-now.weekday()))).replace(hour=9, minute=0),
                'end': (now + timedelta(days=(7-now.weekday()))).replace(hour=10, minute=0),
                'category': 0,  # 회의
                'type': 'meeting',
                'priority': 'medium',
                'location': '회의실 B',
                'description': '이번 주 스프린트 목표 설정',
                'recurrence_type': 'weekly',
                'recurrence_end': now + timedelta(days=90)
            },
        ]

        created_count = 0
        for event_data in events_data:
            # 이미 같은 제목의 이벤트가 있는지 확인
            if CalendarEvent.objects.filter(title=event_data['title'], creator=user).exists():
                continue
            
            event = CalendarEvent.objects.create(
                title=event_data['title'],
                description=event_data.get('description', ''),
                creator=user,
                category=categories[event_data['category']],
                start_datetime=event_data['start'],
                end_datetime=event_data['end'],
                is_all_day=event_data.get('is_all_day', False),
                event_type=event_data.get('type', 'work'),
                priority=event_data.get('priority', 'medium'),
                location=event_data.get('location', ''),
                recurrence_type=event_data.get('recurrence_type', 'none'),
                recurrence_end_date=event_data.get('recurrence_end', None),
                reminder_minutes=30,
                is_active=True
            )
            
            # 작성자를 참석자로 추가
            EventAttendee.objects.create(
                event=event,
                user=user,
                status='accepted'
            )
            
            created_count += 1
            self.stdout.write(self.style.SUCCESS(f'이벤트 생성: {event.title}'))

        self.stdout.write(self.style.SUCCESS(f'\n총 {created_count}개의 샘플 이벤트가 생성되었습니다.'))