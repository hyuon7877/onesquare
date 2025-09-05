"""
OneSquare 통합 캘린더 시스템 - Django Tests
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from datetime import datetime, timedelta
import json

from apps.auth_system.models import CustomUser
from .models import CalendarEvent, CalendarCategory, EventAttendee, CalendarSettings
from .forms import CalendarEventForm, QuickEventForm

User = get_user_model()


class CalendarModelTests(TestCase):
    """캘린더 모델 테스트"""
    
    def setUp(self):
        """테스트 데이터 설정"""
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            user_type='TEAM_MEMBER'
        )
        
        self.manager = CustomUser.objects.create_user(
            username='manager',
            email='manager@example.com',
            password='testpass123',
            user_type='MANAGER'
        )
        
        self.category = CalendarCategory.objects.create(
            name='업무',
            color='#3788d8',
            accessible_user_types=['TEAM_MEMBER', 'MANAGER']
        )
    
    def test_calendar_event_creation(self):
        """캘린더 이벤트 생성 테스트"""
        start_time = timezone.now() + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)
        
        event = CalendarEvent.objects.create(
            title='테스트 이벤트',
            description='테스트용 이벤트입니다.',
            creator=self.user,
            category=self.category,
            start_datetime=start_time,
            end_datetime=end_time,
            event_type=CalendarEvent.EventType.MEETING
        )
        
        self.assertEqual(event.title, '테스트 이벤트')
        self.assertEqual(event.creator, self.user)
        self.assertEqual(event.category, self.category)
        self.assertEqual(event.duration_minutes, 120)
        self.assertFalse(event.is_past)
    
    def test_calendar_event_permissions(self):
        """캘린더 이벤트 권한 테스트"""
        event = CalendarEvent.objects.create(
            title='권한 테스트',
            creator=self.user,
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=1, hours=1),
        )
        
        # 작성자는 편집 가능
        self.assertTrue(event.can_edit(self.user))
        self.assertTrue(event.can_view(self.user))
        
        # 관리자는 편집 가능
        self.assertTrue(event.can_edit(self.manager))
        self.assertTrue(event.can_view(self.manager))
        
        # 다른 사용자 생성
        other_user = CustomUser.objects.create_user(
            username='other',
            email='other@example.com',
            password='testpass123',
            user_type='TEAM_MEMBER'
        )
        
        # 다른 사용자는 편집 불가 (참석자가 아닌 경우)
        self.assertFalse(event.can_edit(other_user))
        # 하지만 조회는 가능 (같은 회사)
        self.assertTrue(event.can_view(other_user))
    
    def test_event_attendee(self):
        """이벤트 참석자 테스트"""
        event = CalendarEvent.objects.create(
            title='참석자 테스트',
            creator=self.user,
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=1, hours=1),
        )
        
        # 참석자 추가
        attendee = EventAttendee.objects.create(
            event=event,
            user=self.manager,
            status=EventAttendee.Status.PENDING
        )
        
        self.assertEqual(attendee.event, event)
        self.assertEqual(attendee.user, self.manager)
        self.assertEqual(attendee.status, EventAttendee.Status.PENDING)
        
        # 참석자는 이벤트 편집 가능
        self.assertTrue(event.can_edit(self.manager))
    
    def test_calendar_category_permissions(self):
        """캘린더 카테고리 권한 테스트"""
        # 접근 가능한 사용자 타입이 설정된 카테고리
        restricted_category = CalendarCategory.objects.create(
            name='관리자 전용',
            accessible_user_types=['SUPER_ADMIN', 'MANAGER']
        )
        
        # 일반 사용자는 접근 불가
        self.assertFalse(restricted_category.can_access(self.user))
        
        # 관리자는 접근 가능
        self.assertTrue(restricted_category.can_access(self.manager))
        
        # 제한 없는 카테고리
        public_category = CalendarCategory.objects.create(
            name='공개 카테고리',
            accessible_user_types=[]
        )
        
        # 모든 사용자 접근 가능
        self.assertTrue(public_category.can_access(self.user))
        self.assertTrue(public_category.can_access(self.manager))
    
    def test_fullcalendar_format(self):
        """FullCalendar 형식 변환 테스트"""
        event = CalendarEvent.objects.create(
            title='FullCalendar 테스트',
            description='테스트 설명',
            creator=self.user,
            category=self.category,
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=1, hours=2),
            location='회의실 A',
            priority=CalendarEvent.Priority.HIGH,
        )
        
        fc_format = event.fullcalendar_format
        
        self.assertEqual(fc_format['id'], str(event.id))
        self.assertEqual(fc_format['title'], event.title)
        self.assertEqual(fc_format['backgroundColor'], self.category.color)
        self.assertEqual(fc_format['extendedProps']['description'], event.description)
        self.assertEqual(fc_format['extendedProps']['location'], event.location)
        self.assertEqual(fc_format['extendedProps']['priority'], event.priority)


class CalendarFormTests(TestCase):
    """캘린더 폼 테스트"""
    
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            user_type='TEAM_MEMBER'
        )
        
        self.category = CalendarCategory.objects.create(
            name='업무',
            accessible_user_types=['TEAM_MEMBER']
        )
    
    def test_calendar_event_form_valid(self):
        """유효한 캘린더 이벤트 폼 테스트"""
        start_time = timezone.now() + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)
        
        form_data = {
            'title': '테스트 이벤트',
            'description': '테스트 설명',
            'category': self.category.id,
            'start_datetime': start_time.strftime('%Y-%m-%dT%H:%M'),
            'end_datetime': end_time.strftime('%Y-%m-%dT%H:%M'),
            'event_type': CalendarEvent.EventType.MEETING,
            'priority': CalendarEvent.Priority.MEDIUM,
            'reminder_minutes': 15,
        }
        
        form = CalendarEventForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
        
        event = form.save()
        self.assertEqual(event.title, '테스트 이벤트')
        self.assertEqual(event.creator, self.user)
    
    def test_calendar_event_form_invalid_time(self):
        """잘못된 시간의 캘린더 이벤트 폼 테스트"""
        start_time = timezone.now() + timedelta(days=1)
        end_time = start_time - timedelta(hours=1)  # 종료시간이 시작시간보다 빠름
        
        form_data = {
            'title': '테스트 이벤트',
            'start_datetime': start_time.strftime('%Y-%m-%dT%H:%M'),
            'end_datetime': end_time.strftime('%Y-%m-%dT%H:%M'),
            'event_type': CalendarEvent.EventType.MEETING,
        }
        
        form = CalendarEventForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('종료일시는 시작일시보다 늦어야 합니다.', str(form.errors))
    
    def test_quick_event_form(self):
        """빠른 이벤트 생성 폼 테스트"""
        start_time = timezone.now() + timedelta(days=1)
        end_time = start_time + timedelta(hours=1)
        
        form_data = {
            'title': '빠른 이벤트',
            'start_datetime': start_time.strftime('%Y-%m-%dT%H:%M'),
            'end_datetime': end_time.strftime('%Y-%m-%dT%H:%M'),
        }
        
        form = QuickEventForm(data=form_data, user=self.user)
        self.assertTrue(form.is_valid())
        
        event = form.save()
        self.assertEqual(event.title, '빠른 이벤트')
        self.assertEqual(event.creator, self.user)
        self.assertEqual(event.event_type, CalendarEvent.EventType.WORK)


class CalendarViewTests(TestCase):
    """캘린더 뷰 테스트"""
    
    def setUp(self):
        self.client = Client()
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            user_type='TEAM_MEMBER'
        )
        self.client.login(username='testuser', password='testpass123')
        
        self.category = CalendarCategory.objects.create(
            name='테스트 카테고리',
            accessible_user_types=['TEAM_MEMBER']
        )
    
    def test_calendar_dashboard_view(self):
        """캘린더 대시보드 뷰 테스트"""
        response = self.client.get(reverse('calendar_system:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '캘린더')
    
    def test_create_event_view_get(self):
        """이벤트 생성 뷰 GET 테스트"""
        response = self.client.get(reverse('calendar_system:create_event'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '새 이벤트')
    
    def test_create_event_view_post(self):
        """이벤트 생성 뷰 POST 테스트"""
        start_time = timezone.now() + timedelta(days=1)
        end_time = start_time + timedelta(hours=2)
        
        data = {
            'title': '테스트 이벤트',
            'description': '테스트 설명',
            'category': self.category.id,
            'start_datetime': start_time.strftime('%Y-%m-%dT%H:%M'),
            'end_datetime': end_time.strftime('%Y-%m-%dT%H:%M'),
            'event_type': CalendarEvent.EventType.MEETING,
            'priority': CalendarEvent.Priority.MEDIUM,
        }
        
        response = self.client.post(reverse('calendar_system:create_event'), data)
        self.assertEqual(response.status_code, 302)  # 리다이렉트
        
        # 이벤트가 생성되었는지 확인
        self.assertTrue(CalendarEvent.objects.filter(title='테스트 이벤트').exists())
    
    def test_calendar_events_api(self):
        """캘린더 이벤트 API 테스트"""
        # 테스트 이벤트 생성
        event = CalendarEvent.objects.create(
            title='API 테스트 이벤트',
            creator=self.user,
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=1, hours=1),
        )
        
        response = self.client.get(reverse('calendar_system:events_api'))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['title'], 'API 테스트 이벤트')
    
    def test_event_detail_view(self):
        """이벤트 상세 뷰 테스트"""
        event = CalendarEvent.objects.create(
            title='상세 테스트 이벤트',
            creator=self.user,
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=1, hours=1),
        )
        
        response = self.client.get(
            reverse('calendar_system:event_detail', args=[event.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, event.title)
    
    def test_my_events_view(self):
        """내 이벤트 목록 뷰 테스트"""
        # 여러 테스트 이벤트 생성
        for i in range(5):
            CalendarEvent.objects.create(
                title=f'이벤트 {i}',
                creator=self.user,
                start_datetime=timezone.now() + timedelta(days=i+1),
                end_datetime=timezone.now() + timedelta(days=i+1, hours=1),
            )
        
        response = self.client.get(reverse('calendar_system:my_events'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '이벤트 0')
        self.assertContains(response, '이벤트 4')
    
    def test_calendar_settings_view(self):
        """캘린더 설정 뷰 테스트"""
        response = self.client.get(reverse('calendar_system:settings'))
        self.assertEqual(response.status_code, 200)
        
        # 설정 변경
        data = {
            'default_view': CalendarSettings.View.WEEK,
            'work_start_time': '09:00',
            'work_end_time': '18:00',
            'default_reminder_minutes': 30,
            'email_notifications': True,
            'push_notifications': True,
            'show_weekends': True,
        }
        
        response = self.client.post(reverse('calendar_system:settings'), data)
        self.assertEqual(response.status_code, 302)
        
        # 설정이 저장되었는지 확인
        settings = CalendarSettings.objects.get(user=self.user)
        self.assertEqual(settings.default_view, CalendarSettings.View.WEEK)
        self.assertEqual(settings.default_reminder_minutes, 30)


class CalendarPermissionTests(TestCase):
    """캘린더 권한 테스트"""
    
    def setUp(self):
        self.client = Client()
        
        # 다양한 사용자 타입 생성
        self.super_admin = CustomUser.objects.create_user(
            username='superadmin',
            email='super@example.com',
            password='testpass123',
            user_type='SUPER_ADMIN'
        )
        
        self.manager = CustomUser.objects.create_user(
            username='manager',
            email='manager@example.com',
            password='testpass123',
            user_type='MANAGER'
        )
        
        self.team_member = CustomUser.objects.create_user(
            username='team',
            email='team@example.com',
            password='testpass123',
            user_type='TEAM_MEMBER'
        )
        
        self.partner = CustomUser.objects.create_user(
            username='partner',
            email='partner@example.com',
            password='testpass123',
            user_type='PARTNER'
        )
    
    def test_manager_can_view_all_events(self):
        """관리자는 모든 이벤트를 볼 수 있어야 함"""
        # 팀원이 만든 이벤트
        team_event = CalendarEvent.objects.create(
            title='팀원 이벤트',
            creator=self.team_member,
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=1, hours=1),
        )
        
        self.client.login(username='manager', password='testpass123')
        response = self.client.get(reverse('calendar_system:events_api'))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        event_titles = [event['title'] for event in data]
        self.assertIn('팀원 이벤트', event_titles)
    
    def test_partner_can_only_view_own_events(self):
        """파트너는 자신의 이벤트만 볼 수 있어야 함"""
        # 팀원이 만든 이벤트
        team_event = CalendarEvent.objects.create(
            title='팀원 이벤트',
            creator=self.team_member,
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=1, hours=1),
        )
        
        # 파트너가 만든 이벤트
        partner_event = CalendarEvent.objects.create(
            title='파트너 이벤트',
            creator=self.partner,
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=1, hours=1),
        )
        
        self.client.login(username='partner', password='testpass123')
        response = self.client.get(reverse('calendar_system:events_api'))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        event_titles = [event['title'] for event in data]
        self.assertIn('파트너 이벤트', event_titles)
        self.assertNotIn('팀원 이벤트', event_titles)
    
    def test_unauthorized_event_edit_attempt(self):
        """권한 없는 이벤트 편집 시도 테스트"""
        # 관리자가 만든 이벤트
        manager_event = CalendarEvent.objects.create(
            title='관리자 이벤트',
            creator=self.manager,
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=1, hours=1),
        )
        
        # 파트너로 로그인하여 편집 시도
        self.client.login(username='partner', password='testpass123')
        response = self.client.get(
            reverse('calendar_system:edit_event', args=[manager_event.id])
        )
        
        # 권한이 없으므로 리다이렉트 되어야 함
        self.assertEqual(response.status_code, 302)