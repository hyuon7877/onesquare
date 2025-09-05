"""
OneSquare 권한 시스템 테스트

권한 매트릭스, 권한 확인, 뷰 접근 제어 등을 테스트합니다.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.core.management import call_command
from django.core.exceptions import PermissionDenied
from .models import CustomUser, UserType, UserGroup
from .permissions import (
    PermissionManager, SystemModule, PermissionLevel,
    PERMISSION_MATRIX, SYSTEM_PERMISSIONS
)
from .views import PermissionRequiredMixin


class PermissionMatrixTestCase(TestCase):
    """권한 매트릭스 테스트"""
    
    def setUp(self):
        """테스트 데이터 설정"""
        # 권한 시스템 초기화
        call_command('setup_permissions', verbosity=0)
        
        # 각 사용자 타입별 테스트 사용자 생성
        self.super_admin = CustomUser.objects.create_user(
            username='super_admin',
            email='super@test.com',
            password='testpass123',
            user_type=UserType.SUPER_ADMIN,
            is_approved=True
        )
        
        self.manager = CustomUser.objects.create_user(
            username='manager',
            email='manager@test.com', 
            password='testpass123',
            user_type=UserType.MANAGER,
            is_approved=True
        )
        
        self.team_member = CustomUser.objects.create_user(
            username='team_member',
            email='team@test.com',
            password='testpass123', 
            user_type=UserType.TEAM_MEMBER,
            is_approved=True
        )
        
        self.partner = CustomUser.objects.create_user(
            username='partner',
            email='partner@test.com',
            password='testpass123',
            user_type=UserType.PARTNER,
            is_approved=True
        )
        
        self.contractor = CustomUser.objects.create_user(
            username='contractor',
            email='contractor@test.com',
            password='testpass123',
            user_type=UserType.CONTRACTOR,
            is_approved=True
        )
        
        # 권한 할당
        for user in [self.super_admin, self.manager, self.team_member, self.partner, self.contractor]:
            user.assign_user_type_permissions()
    
    def test_permission_matrix_completeness(self):
        """권한 매트릭스 완전성 테스트"""
        # 모든 사용자 타입이 매트릭스에 정의되어 있는지 확인
        for user_type in UserType:
            self.assertIn(user_type.value, PERMISSION_MATRIX)
        
        # 모든 시스템 모듈이 각 사용자 타입에 정의되어 있는지 확인
        for user_type in UserType:
            user_permissions = PERMISSION_MATRIX[user_type.value]
            for module in SystemModule:
                self.assertIn(module, user_permissions)
    
    def test_super_admin_permissions(self):
        """최고관리자 권한 테스트"""
        user = self.super_admin
        
        # 모든 모듈에 대해 FULL 권한 확인
        for module in SystemModule:
            self.assertTrue(
                user.has_system_permission(module, PermissionLevel.FULL),
                f"Super Admin should have FULL access to {module.value}"
            )
    
    def test_manager_permissions(self):
        """중간관리자 권한 테스트"""
        user = self.manager
        
        # 대시보드는 FULL 권한
        self.assertTrue(user.has_system_permission(SystemModule.DASHBOARD, PermissionLevel.FULL))
        
        # 사용자 관리는 READ_WRITE 권한
        self.assertTrue(user.has_system_permission(SystemModule.USER_MANAGEMENT, PermissionLevel.READ_WRITE))
        self.assertFalse(user.has_system_permission(SystemModule.USER_MANAGEMENT, PermissionLevel.FULL))
        
        # ADMIN 모듈은 접근 불가
        self.assertFalse(user.has_system_permission(SystemModule.ADMIN, PermissionLevel.READ_ONLY))
    
    def test_team_member_permissions(self):
        """팀원 권한 테스트"""
        user = self.team_member
        
        # 기본 모듈들은 READ_ONLY 권한
        self.assertTrue(user.has_system_permission(SystemModule.DASHBOARD, PermissionLevel.READ_ONLY))
        self.assertTrue(user.has_system_permission(SystemModule.CALENDAR, PermissionLevel.READ_ONLY))
        
        # 사용자 관리는 접근 불가
        self.assertFalse(user.has_system_permission(SystemModule.USER_MANAGEMENT, PermissionLevel.READ_ONLY))
        
        # ADMIN 모듈은 접근 불가
        self.assertFalse(user.has_system_permission(SystemModule.ADMIN, PermissionLevel.READ_ONLY))
    
    def test_partner_permissions(self):
        """파트너 권한 테스트"""
        user = self.partner
        
        # 제한된 모듈만 접근 가능
        self.assertTrue(user.has_system_permission(SystemModule.DASHBOARD, PermissionLevel.READ_ONLY))
        self.assertTrue(user.has_system_permission(SystemModule.FIELD_REPORTS, PermissionLevel.READ_WRITE))
        
        # 사용자 관리는 접근 불가
        self.assertFalse(user.has_system_permission(SystemModule.USER_MANAGEMENT, PermissionLevel.READ_ONLY))
    
    def test_contractor_permissions(self):
        """도급사 권한 테스트"""
        user = self.contractor
        
        # 제한된 모듈만 접근 가능  
        self.assertTrue(user.has_system_permission(SystemModule.FIELD_REPORTS, PermissionLevel.READ_WRITE))
        self.assertTrue(user.has_system_permission(SystemModule.CALENDAR, PermissionLevel.READ_ONLY))
        
        # 관리 기능은 접근 불가
        self.assertFalse(user.has_system_permission(SystemModule.USER_MANAGEMENT, PermissionLevel.READ_ONLY))
        self.assertFalse(user.has_system_permission(SystemModule.ADMIN, PermissionLevel.READ_ONLY))


class PermissionManagerTestCase(TestCase):
    """PermissionManager 클래스 테스트"""
    
    def setUp(self):
        call_command('setup_permissions', verbosity=0)
        
        self.user = CustomUser.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            user_type=UserType.TEAM_MEMBER,
            is_approved=True
        )
        self.user.assign_user_type_permissions()
    
    def test_has_permission(self):
        """커스텀 권한 확인 테스트"""
        # 팀원이 대시보드 조회 권한을 가지는지 확인
        self.assertTrue(
            PermissionManager.has_permission(self.user, 'view_dashboard')
        )
        
        # 팀원이 사용자 관리 권한을 가지지 않는지 확인
        self.assertFalse(
            PermissionManager.has_permission(self.user, 'add_user_management')
        )
    
    def test_has_module_permission(self):
        """모듈 권한 확인 테스트"""
        # 팀원의 대시보드 READ_ONLY 권한 확인
        self.assertTrue(
            PermissionManager.has_module_permission(
                self.user, 
                SystemModule.DASHBOARD, 
                PermissionLevel.READ_ONLY
            )
        )
        
        # 팀원의 사용자 관리 권한 없음 확인
        self.assertFalse(
            PermissionManager.has_module_permission(
                self.user,
                SystemModule.USER_MANAGEMENT,
                PermissionLevel.READ_ONLY
            )
        )


class PermissionViewTestCase(TestCase):
    """권한 기반 뷰 접근 제어 테스트"""
    
    def setUp(self):
        call_command('setup_permissions', verbosity=0)
        self.client = Client()
        
        # 테스트 사용자들
        self.super_admin = CustomUser.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            user_type=UserType.SUPER_ADMIN,
            is_approved=True
        )
        
        self.team_member = CustomUser.objects.create_user(
            username='member',
            email='member@test.com',
            password='testpass123',
            user_type=UserType.TEAM_MEMBER,
            is_approved=True
        )
        
        # 권한 할당
        self.super_admin.assign_user_type_permissions()
        self.team_member.assign_user_type_permissions()
    
    def test_permission_required_mixin_success(self):
        """PermissionRequiredMixin 성공 케이스 테스트"""
        # 가상의 뷰 클래스 생성
        class TestView(PermissionRequiredMixin):
            required_module = SystemModule.DASHBOARD
            required_level = PermissionLevel.READ_ONLY
            
            def dispatch(self, request, *args, **kwargs):
                # 권한 확인 후 성공 시뮬레이션
                return super().dispatch(request, *args, **kwargs)
        
        # 권한이 있는 사용자로 테스트
        from unittest.mock import Mock
        request = Mock()
        request.user = self.super_admin
        
        view = TestView()
        
        # 권한 확인이 통과해야 함 (예외가 발생하지 않아야 함)
        try:
            super(PermissionRequiredMixin, view).dispatch(request)
            permission_passed = True
        except PermissionDenied:
            permission_passed = False
        
        self.assertTrue(permission_passed)
    
    def test_permission_required_mixin_failure(self):
        """PermissionRequiredMixin 실패 케이스 테스트"""
        class TestView(PermissionRequiredMixin):
            required_module = SystemModule.USER_MANAGEMENT
            required_level = PermissionLevel.READ_ONLY
            required_user_types = [UserType.SUPER_ADMIN, UserType.MANAGER]
        
        from unittest.mock import Mock
        request = Mock()
        request.user = self.team_member  # 권한이 없는 사용자
        
        view = TestView()
        
        # 권한 없음으로 인해 PermissionDenied 예외가 발생해야 함
        with self.assertRaises(PermissionDenied):
            view.dispatch(request)
    
    def test_unapproved_user_access(self):
        """승인되지 않은 사용자 접근 테스트"""
        unapproved_user = CustomUser.objects.create_user(
            username='unapproved',
            email='unapproved@test.com',
            password='testpass123',
            user_type=UserType.TEAM_MEMBER,
            is_approved=False  # 승인되지 않음
        )
        
        class TestView(PermissionRequiredMixin):
            required_module = SystemModule.DASHBOARD
            required_level = PermissionLevel.READ_ONLY
        
        from unittest.mock import Mock
        request = Mock()
        request.user = unapproved_user
        
        view = TestView()
        
        # 승인되지 않은 사용자는 접근할 수 없어야 함
        with self.assertRaises(PermissionDenied):
            view.dispatch(request)


class PermissionAPITestCase(TestCase):
    """권한 관련 API 테스트"""
    
    def setUp(self):
        call_command('setup_permissions', verbosity=0)
        self.client = Client()
        
        self.admin_user = CustomUser.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            user_type=UserType.SUPER_ADMIN,
            is_approved=True
        )
        
        self.regular_user = CustomUser.objects.create_user(
            username='regular',
            email='regular@test.com',
            password='testpass123',
            user_type=UserType.TEAM_MEMBER,
            is_approved=True
        )
        
        # 권한 할당
        self.admin_user.assign_user_type_permissions()
        self.regular_user.assign_user_type_permissions()
    
    def test_user_permissions_api(self):
        """사용자 권한 조회 API 테스트"""
        self.client.force_login(self.admin_user)
        
        response = self.client.get('/api/auth/permissions/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # 응답 구조 확인
        self.assertIn('user_info', data)
        self.assertIn('permissions', data)
        self.assertIn('accessible_modules', data)
        
        # 관리자 정보 확인
        self.assertEqual(data['user_info']['username'], 'admin')
        self.assertEqual(data['user_info']['user_type'], UserType.SUPER_ADMIN)
        self.assertTrue(data['has_admin_access'])
    
    def test_check_module_permission_api(self):
        """모듈 권한 확인 API 테스트"""
        self.client.force_login(self.regular_user)
        
        # 대시보드 권한 확인 (팀원은 READ_ONLY 권한 있음)
        response = self.client.get('/api/auth/permissions/check/dashboard/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['has_read'])
        self.assertFalse(data['has_write'])
        self.assertFalse(data['has_full'])
        
        # 사용자 관리 권한 확인 (팀원은 권한 없음)
        response = self.client.get('/api/auth/permissions/check/user_management/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertFalse(data['has_read'])
        self.assertFalse(data['has_write'])
        self.assertFalse(data['has_full'])


class PermissionManagementCommandTestCase(TestCase):
    """권한 관리 명령어 테스트"""
    
    def test_setup_permissions_command(self):
        """setup_permissions 명령어 테스트"""
        from io import StringIO
        from django.core.management import call_command
        
        out = StringIO()
        
        # 명령어 실행
        call_command('setup_permissions', stdout=out)
        
        # 그룹 생성 확인
        self.assertTrue(Group.objects.filter(name='OneSquare_super_admin').exists())
        self.assertTrue(Group.objects.filter(name='OneSquare_manager').exists())
        self.assertTrue(Group.objects.filter(name='OneSquare_team_member').exists())
        
        # UserGroup 확장 정보 생성 확인
        self.assertTrue(UserGroup.objects.filter(user_type='super_admin').exists())
        self.assertTrue(UserGroup.objects.filter(user_type='manager').exists())
        
        # 권한 생성 확인
        user_content_type = ContentType.objects.get_for_model(CustomUser)
        self.assertTrue(
            Permission.objects.filter(
                codename='view_dashboard',
                content_type=user_content_type
            ).exists()
        )
    
    def test_dry_run_mode(self):
        """드라이 런 모드 테스트"""
        from io import StringIO
        from django.core.management import call_command
        
        out = StringIO()
        
        # 드라이 런으로 명령어 실행
        call_command('setup_permissions', dry_run=True, stdout=out)
        
        # 실제로 생성되지 않아야 함
        self.assertFalse(Group.objects.filter(name='OneSquare_super_admin').exists())
        
        # 출력에 DRY RUN 메시지가 포함되어야 함
        output = out.getvalue()
        self.assertIn('DRY RUN', output)


if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['apps.auth_system.test_permissions'])