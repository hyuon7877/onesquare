"""
OneSquare 사용자 그룹 설정 관리 명령

사용법:
python manage.py setup_groups
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.auth_system.models import UserGroup, UserType
from apps.auth_system.signals import create_default_groups


class Command(BaseCommand):
    help = 'OneSquare 시스템의 기본 사용자 그룹 및 권한을 설정합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='기존 그룹을 모두 삭제하고 다시 생성합니다.',
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='상세한 진행 상황을 출력합니다.',
        )

    def handle(self, *args, **options):
        self.verbose = options['verbose']
        
        if options['reset']:
            self.stdout.write(
                self.style.WARNING('기존 그룹들을 삭제하고 다시 생성합니다...')
            )
            self.reset_groups()
        
        self.stdout.write('사용자 그룹 설정을 시작합니다...')
        
        try:
            # 기본 그룹 생성
            created_groups = create_default_groups()
            
            # 각 그룹에 권한 할당
            self.setup_permissions()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ {len(created_groups)}개의 사용자 그룹이 성공적으로 설정되었습니다!'
                )
            )
            
            # 그룹 정보 출력
            self.display_groups_info()
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 그룹 설정 중 오류 발생: {e}')
            )
            raise

    def reset_groups(self):
        """기존 그룹 삭제"""
        try:
            # UserGroup과 연결된 Group들만 삭제
            user_groups = UserGroup.objects.all()
            for ug in user_groups:
                group_name = ug.group.name
                ug.group.delete()  # Group 삭제 시 UserGroup도 CASCADE로 삭제됨
                if self.verbose:
                    self.stdout.write(f'  - 삭제됨: {group_name}')
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ {user_groups.count()}개의 기존 그룹이 삭제되었습니다.')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 그룹 삭제 중 오류: {e}')
            )

    def setup_permissions(self):
        """각 그룹에 Django 권한 할당"""
        try:
            # ContentType 가져오기
            from apps.auth_system.models import CustomUser, OTPCode, UserSession
            from apps.notion_api import models as notion_models
            from apps.dashboard import models as dashboard_models
            from apps.calendar_system import models as calendar_models
            from apps.field_reports import models as field_models
            
            user_ct = ContentType.objects.get_for_model(CustomUser)
            
            # 그룹별 권한 설정
            permission_mapping = {
                UserType.SUPER_ADMIN: [
                    # 모든 권한 (superuser 권한)
                    'auth.add_user', 'auth.change_user', 'auth.delete_user', 'auth.view_user',
                    'auth.add_group', 'auth.change_group', 'auth.delete_group', 'auth.view_group',
                ],
                UserType.MANAGER: [
                    # 관리자 권한 (사용자 관리 제외)
                    'auth.view_user', 'auth.change_user',
                ],
                UserType.TEAM_MEMBER: [
                    # 기본 직원 권한
                    'auth.view_user',
                ],
                UserType.PARTNER: [
                    # 파트너 권한 (현장 리포트만)
                ],
                UserType.CONTRACTOR: [
                    # 도급사 권한 (현장 리포트만)
                ],
                UserType.CUSTOM: [
                    # 커스텀 권한 (비어있음, 개별 설정)
                ],
            }
            
            for user_group_info in UserGroup.objects.all():
                group = user_group_info.group
                user_type = user_group_info.user_type
                
                # 기존 권한 제거
                group.permissions.clear()
                
                # 새 권한 추가
                permission_codenames = permission_mapping.get(user_type, [])
                
                for codename in permission_codenames:
                    try:
                        app_label, perm_codename = codename.split('.')
                        permission = Permission.objects.get(
                            content_type__app_label=app_label,
                            codename=perm_codename
                        )
                        group.permissions.add(permission)
                        
                        if self.verbose:
                            self.stdout.write(f'  - {group.name}에 권한 추가: {codename}')
                    except Permission.DoesNotExist:
                        if self.verbose:
                            self.stdout.write(
                                self.style.WARNING(f'  - 권한을 찾을 수 없음: {codename}')
                            )
                        continue
                
                if self.verbose:
                    self.stdout.write(
                        f'✅ {group.name} 그룹 권한 설정 완료 ({group.permissions.count()}개 권한)'
                    )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 권한 설정 중 오류: {e}')
            )

    def display_groups_info(self):
        """생성된 그룹 정보 출력"""
        self.stdout.write('\n📋 생성된 사용자 그룹 정보:')
        self.stdout.write('-' * 80)
        
        for user_group_info in UserGroup.objects.all().order_by('user_type'):
            group = user_group_info.group
            
            # 권한 요약
            permissions = []
            if user_group_info.can_access_dashboard:
                permissions.append('대시보드')
            if user_group_info.can_manage_users:
                permissions.append('사용자관리')
            if user_group_info.can_view_reports:
                permissions.append('리포트')
            if user_group_info.can_manage_calendar:
                permissions.append('캘린더')
            if user_group_info.can_access_field_reports:
                permissions.append('현장리포트')
            
            permissions_str = ', '.join(permissions) if permissions else '없음'
            
            self.stdout.write(
                f"🏷️  {group.name} ({user_group_info.get_user_type_display()})"
            )
            self.stdout.write(f"   📝 설명: {user_group_info.description}")
            self.stdout.write(f"   🔑 권한: {permissions_str}")
            self.stdout.write(f"   👥 사용자 수: {group.user_set.count()}명")
            self.stdout.write(f"   🛡️  Django 권한 수: {group.permissions.count()}개")
            self.stdout.write('')
        
        self.stdout.write('-' * 80)
        self.stdout.write(
            f'📊 총 {UserGroup.objects.count()}개 그룹, '
            f'{Group.objects.count()}개 Django 그룹이 설정되었습니다.'
        )