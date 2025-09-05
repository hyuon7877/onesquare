"""
OneSquare 사용자 인증 시스템 - 테스트

이 모듈은 인증 시스템의 모든 기능에 대한 포괄적인 테스트를 제공합니다.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from unittest.mock import patch
import json

from .models import CustomUser, OTPCode, UserSession, UserGroup, UserType, AuthMethod
from .utils import OTPGenerator, UserPermissionChecker, SessionManager
from .serializers import (
    UserRegistrationSerializer,
    OTPRequestSerializer,
    EmailPasswordLoginSerializer
)

User = get_user_model()


class CustomUserModelTest(TestCase):
    """CustomUser 모델 테스트"""
    
    def setUp(self):
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': '테스트',
            'last_name': '사용자',
            'user_type': UserType.TEAM_MEMBER,
            'phone_number': '010-1234-5678'
        }
    
    def test_create_user(self):
        """일반 사용자 생성 테스트"""
        user = CustomUser.objects.create_user(
            username=self.user_data['username'],
            email=self.user_data['email'],
            password='testpass123!',
            **{k: v for k, v in self.user_data.items() if k not in ['username', 'email']}
        )
        
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('testpass123!'))
        self.assertEqual(user.user_type, UserType.TEAM_MEMBER)
        self.assertTrue(user.is_approved)  # 기본값
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
    
    def test_create_partner_user(self):
        """파트너 사용자 생성 테스트"""
        user = CustomUser.objects.create_user(
            username='partner1',
            email='partner@company.com',
            password='testpass123!',
            user_type=UserType.PARTNER,
            phone_number='010-9876-5432',
            company='파트너사'
        )
        
        self.assertEqual(user.user_type, UserType.PARTNER)
        self.assertFalse(user.is_approved)  # 파트너는 기본적으로 미승인
        self.assertEqual(user.auth_method, AuthMethod.OTP_SMS)  # 기본 OTP 인증
    
    def test_user_properties(self):
        """사용자 속성 메서드 테스트"""
        user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123!',
            user_type=UserType.PARTNER,
            auth_method=AuthMethod.OTP_SMS
        )
        
        self.assertTrue(user.is_partner)
        self.assertFalse(user.is_contractor)
        self.assertTrue(user.requires_otp)
    
    def test_phone_validation(self):
        """전화번호 유효성 검사 테스트"""
        # 유효한 전화번호
        user = CustomUser(phone_number='010-1234-5678')
        user.full_clean()  # 유효성 검사 실행
        
        # 유효하지 않은 전화번호
        user.phone_number = '123-456'
        with self.assertRaises(Exception):
            user.full_clean()


class OTPCodeModelTest(TestCase):
    """OTPCode 모델 테스트"""
    
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123!',
            phone_number='010-1234-5678'
        )
    
    def test_create_otp_code(self):
        """OTP 코드 생성 테스트"""
        otp = OTPCode.objects.create(
            user=self.user,
            code='123456',
            delivery_method='sms',
            delivery_target='010-1234-5678'
        )
        
        self.assertEqual(len(otp.code), 6)
        self.assertFalse(otp.is_used)
        self.assertFalse(otp.is_expired)
    
    def test_otp_expiration(self):
        """OTP 만료 테스트"""
        # 과거 시간으로 설정하여 만료된 OTP 생성
        import datetime
        otp = OTPCode.objects.create(
            user=self.user,
            code='123456',
            delivery_method='sms',
            delivery_target='010-1234-5678'
        )
        
        # 생성 시간을 과거로 설정
        otp.created_at = timezone.now() - datetime.timedelta(minutes=10)
        otp.save()
        
        self.assertTrue(otp.is_expired)
    
    def test_mark_as_used(self):
        """OTP 사용 처리 테스트"""
        otp = OTPCode.objects.create(
            user=self.user,
            code='123456',
            delivery_method='sms',
            delivery_target='010-1234-5678'
        )
        
        otp.mark_as_used()
        self.assertTrue(otp.is_used)
        self.assertIsNotNone(otp.used_at)


class OTPGeneratorTest(TestCase):
    """OTPGenerator 유틸리티 테스트"""
    
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123!',
            phone_number='010-1234-5678'
        )
    
    def test_generate_code(self):
        """OTP 코드 생성 테스트"""
        code = OTPGenerator.generate_code()
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())
    
    def test_create_otp_for_user(self):
        """사용자용 OTP 생성 테스트"""
        otp = OTPGenerator.create_otp_for_user(
            user=self.user,
            delivery_method='sms'
        )
        
        self.assertIsNotNone(otp)
        self.assertEqual(otp.user, self.user)
        self.assertEqual(otp.delivery_method, 'sms')
        self.assertEqual(otp.delivery_target, self.user.phone_number)
    
    def test_verify_otp_success(self):
        """OTP 검증 성공 테스트"""
        otp = OTPGenerator.create_otp_for_user(
            user=self.user,
            delivery_method='sms'
        )
        
        result = OTPGenerator.verify_otp(
            user=self.user,
            code=otp.code,
            delivery_method='sms'
        )
        
        self.assertTrue(result)
        
        # 사용됨으로 표시되었는지 확인
        otp.refresh_from_db()
        self.assertTrue(otp.is_used)
    
    def test_verify_otp_failure(self):
        """OTP 검증 실패 테스트"""
        OTPGenerator.create_otp_for_user(
            user=self.user,
            delivery_method='sms'
        )
        
        # 잘못된 코드로 검증
        result = OTPGenerator.verify_otp(
            user=self.user,
            code='000000',
            delivery_method='sms'
        )
        
        self.assertFalse(result)


class UserRegistrationAPITest(APITestCase):
    """사용자 등록 API 테스트"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('auth_system:user_register')
    
    def test_register_team_member(self):
        """팀원 등록 테스트"""
        data = {
            'username': 'teammember1',
            'email': 'team@company.com',
            'password': 'TestPass123!',
            'password_confirm': 'TestPass123!',
            'first_name': '팀',
            'last_name': '멤버',
            'user_type': UserType.TEAM_MEMBER,
            'auth_method': AuthMethod.EMAIL_PASSWORD
        }
        
        response = self.client.post(self.register_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data['approval_required'])
        
        # 사용자가 생성되었는지 확인
        user = CustomUser.objects.get(username='teammember1')
        self.assertTrue(user.is_approved)
    
    def test_register_partner(self):
        """파트너 등록 테스트"""
        data = {
            'username': 'partner1',
            'email': 'partner@company.com',
            'password': 'TestPass123!',
            'password_confirm': 'TestPass123!',
            'first_name': '파트너',
            'last_name': '사용자',
            'user_type': UserType.PARTNER,
            'phone_number': '010-9876-5432',
            'company': '파트너사'
        }
        
        response = self.client.post(self.register_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['approval_required'])
        
        # 파트너는 승인 대기 상태
        user = CustomUser.objects.get(username='partner1')
        self.assertFalse(user.is_approved)
        self.assertEqual(user.auth_method, AuthMethod.OTP_SMS)
    
    def test_register_invalid_password(self):
        """잘못된 비밀번호로 등록 테스트"""
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': '123',  # 너무 약한 비밀번호
            'password_confirm': '123',
            'user_type': UserType.TEAM_MEMBER
        }
        
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class OTPAuthenticationAPITest(APITestCase):
    """OTP 인증 API 테스트"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            username='partner1',
            email='partner@company.com',
            password='TestPass123!',
            user_type=UserType.PARTNER,
            phone_number='010-1234-5678',
            is_approved=True
        )
        self.otp_request_url = reverse('auth_system:otp_request')
        self.otp_verify_url = reverse('auth_system:otp_verify')
    
    @patch('apps.auth_system.utils.SMSService.send_otp_sms')
    def test_otp_request_sms(self, mock_sms_send):
        """SMS OTP 요청 테스트"""
        mock_sms_send.return_value = True
        
        data = {
            'username': 'partner1',
            'delivery_method': 'sms'
        }
        
        response = self.client.post(self.otp_request_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('전송되었습니다', response.data['message'])
        
        # OTP 코드가 생성되었는지 확인
        otp = OTPCode.objects.filter(user=self.user, delivery_method='sms').first()
        self.assertIsNotNone(otp)
        self.assertFalse(otp.is_used)
    
    def test_otp_verification_success(self):
        """OTP 검증 성공 테스트"""
        # OTP 생성
        otp = OTPGenerator.create_otp_for_user(
            user=self.user,
            delivery_method='sms'
        )
        
        data = {
            'username': 'partner1',
            'otp_code': otp.code,
            'delivery_method': 'sms'
        }
        
        response = self.client.post(self.otp_verify_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], '로그인 성공')
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
    
    def test_otp_verification_failure(self):
        """OTP 검증 실패 테스트"""
        data = {
            'username': 'partner1',
            'otp_code': '000000',
            'delivery_method': 'sms'
        }
        
        response = self.client.post(self.otp_verify_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('잘못된 인증코드', response.data['error'])


class EmailPasswordLoginAPITest(APITestCase):
    """이메일+비밀번호 로그인 API 테스트"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            username='manager1',
            email='manager@company.com',
            password='TestPass123!',
            user_type=UserType.MANAGER,
            is_approved=True
        )
        self.login_url = reverse('auth_system:email_login')
    
    def test_email_login_success(self):
        """이메일 로그인 성공 테스트"""
        data = {
            'email': 'manager@company.com',
            'password': 'TestPass123!'
        }
        
        response = self.client.post(self.login_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], '로그인 성공')
        self.assertIn('token', response.data)
        self.assertIn('permissions', response.data)
    
    def test_email_login_failure(self):
        """이메일 로그인 실패 테스트"""
        data = {
            'email': 'manager@company.com',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(self.login_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('올바르지 않습니다', response.data['error'])
    
    def test_unapproved_user_login(self):
        """미승인 사용자 로그인 테스트"""
        self.user.is_approved = False
        self.user.save()
        
        data = {
            'email': 'manager@company.com',
            'password': 'TestPass123!'
        }
        
        response = self.client.post(self.login_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('승인되지 않은', response.data['error'])


class UserPermissionTest(TestCase):
    """사용자 권한 테스트"""
    
    def setUp(self):
        # 테스트용 그룹 생성
        from .signals import create_default_groups
        create_default_groups()
        
        self.super_admin = CustomUser.objects.create_user(
            username='admin',
            email='admin@company.com',
            password='TestPass123!',
            user_type=UserType.SUPER_ADMIN
        )
        
        self.manager = CustomUser.objects.create_user(
            username='manager',
            email='manager@company.com',
            password='TestPass123!',
            user_type=UserType.MANAGER
        )
        
        self.team_member = CustomUser.objects.create_user(
            username='member',
            email='member@company.com',
            password='TestPass123!',
            user_type=UserType.TEAM_MEMBER
        )
        
        self.partner = CustomUser.objects.create_user(
            username='partner',
            email='partner@company.com',
            password='TestPass123!',
            user_type=UserType.PARTNER
        )
    
    def test_dashboard_access_permissions(self):
        """대시보드 접근 권한 테스트"""
        self.assertTrue(UserPermissionChecker.has_dashboard_access(self.super_admin))
        self.assertTrue(UserPermissionChecker.has_dashboard_access(self.manager))
        self.assertTrue(UserPermissionChecker.has_dashboard_access(self.team_member))
        self.assertFalse(UserPermissionChecker.has_dashboard_access(self.partner))
    
    def test_user_management_permissions(self):
        """사용자 관리 권한 테스트"""
        self.assertTrue(UserPermissionChecker.can_manage_users(self.super_admin))
        self.assertTrue(UserPermissionChecker.can_manage_users(self.manager))
        self.assertFalse(UserPermissionChecker.can_manage_users(self.team_member))
        self.assertFalse(UserPermissionChecker.can_manage_users(self.partner))
    
    def test_field_reports_access(self):
        """현장 리포트 접근 권한 테스트"""
        self.assertTrue(UserPermissionChecker.can_access_field_reports(self.super_admin))
        self.assertTrue(UserPermissionChecker.can_access_field_reports(self.manager))
        self.assertFalse(UserPermissionChecker.can_access_field_reports(self.team_member))
        self.assertTrue(UserPermissionChecker.can_access_field_reports(self.partner))


class SessionManagementTest(TestCase):
    """세션 관리 테스트"""
    
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
    
    def test_session_creation(self):
        """세션 생성 테스트"""
        session = UserSession.objects.create(
            user=self.user,
            session_key='test_session_key',
            ip_address='127.0.0.1',
            user_agent='Test Browser'
        )
        
        self.assertTrue(session.is_active)
        self.assertEqual(session.user, self.user)
    
    def test_session_cleanup(self):
        """만료된 세션 정리 테스트"""
        # 오래된 세션 생성
        import datetime
        old_session = UserSession.objects.create(
            user=self.user,
            session_key='old_session',
            ip_address='127.0.0.1',
            user_agent='Test Browser'
        )
        
        # 마지막 활동 시간을 과거로 설정
        old_session.last_activity = timezone.now() - datetime.timedelta(hours=3)
        old_session.save()
        
        # 세션 정리 실행
        cleaned_count = SessionManager.cleanup_expired_sessions()
        
        self.assertGreater(cleaned_count, 0)
        
        # 세션이 비활성화되었는지 확인
        old_session.refresh_from_db()
        self.assertFalse(old_session.is_active)


class AuthenticationIntegrationTest(APITestCase):
    """인증 시스템 통합 테스트"""
    
    def setUp(self):
        self.client = APIClient()
        # 기본 그룹 생성
        from .signals import create_default_groups
        create_default_groups()
    
    def test_full_registration_and_login_flow(self):
        """전체 등록 및 로그인 플로우 테스트"""
        # 1. 사용자 등록
        register_data = {
            'username': 'newuser',
            'email': 'newuser@company.com',
            'password': 'TestPass123!',
            'password_confirm': 'TestPass123!',
            'first_name': '신규',
            'last_name': '사용자',
            'user_type': UserType.TEAM_MEMBER
        }
        
        register_response = self.client.post(
            reverse('auth_system:user_register'),
            register_data
        )
        
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        
        # 2. 로그인
        login_data = {
            'email': 'newuser@company.com',
            'password': 'TestPass123!'
        }
        
        login_response = self.client.post(
            reverse('auth_system:email_login'),
            login_data
        )
        
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        token = login_response.data['token']
        
        # 3. 인증된 요청
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        profile_response = self.client.get(reverse('auth_system:user_profile'))
        
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.data['username'], 'newuser')
    
    @patch('apps.auth_system.utils.SMSService.send_otp_sms')
    def test_partner_otp_flow(self, mock_sms_send):
        """파트너 OTP 인증 플로우 테스트"""
        mock_sms_send.return_value = True
        
        # 1. 파트너 등록 (관리자가 승인해야 함)
        partner = CustomUser.objects.create_user(
            username='partner1',
            email='partner@company.com',
            password='TestPass123!',
            user_type=UserType.PARTNER,
            phone_number='010-1234-5678',
            is_approved=True  # 승인된 상태로 생성
        )
        
        # 2. OTP 요청
        otp_request_data = {
            'username': 'partner1',
            'delivery_method': 'sms'
        }
        
        otp_response = self.client.post(
            reverse('auth_system:otp_request'),
            otp_request_data
        )
        
        self.assertEqual(otp_response.status_code, status.HTTP_200_OK)
        
        # 3. OTP 검증 및 로그인
        otp_code = OTPCode.objects.filter(user=partner).first()
        
        verify_data = {
            'username': 'partner1',
            'otp_code': otp_code.code,
            'delivery_method': 'sms'
        }
        
        verify_response = self.client.post(
            reverse('auth_system:otp_verify'),
            verify_data
        )
        
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        self.assertIn('token', verify_response.data)