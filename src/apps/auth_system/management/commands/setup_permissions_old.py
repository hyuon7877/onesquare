"""
OneSquare 권한 시스템 초기화 Management Command

Django Groups와 Permissions를 생성하고 사용자 타입별 권한을 할당합니다.
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from apps.auth_system.models import CustomUser, UserType, UserGroup
from apps.auth_system.permissions import (
    PERMISSION_MATRIX, SystemModule, PermissionLevel,
    SYSTEM_PERMISSIONS, GROUP_DESCRIPTIONS
)


class Command(BaseCommand):
    help = 'OneSquare 권한 시스템을 초기화합니다. Groups, Permissions, UserGroups를 생성합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='기존 권한 설정을 강제로 덮어씁니다.'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 변경 없이 실행 계획만 출력합니다.'
        )

    def handle(self, *args, **options):
        """권한 시스템 초기화 실행"""
        self.dry_run = options['dry_run']
        self.force = options['force']
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('[DRY RUN] 실제 변경 없이 실행 계획을 출력합니다.')
            )

        try:
            with transaction.atomic():
                self.create_system_permissions()
                self.create_user_groups()
                self.assign_group_permissions()
                self.update_existing_users()
                
                if self.dry_run:
                    # 트랜잭션 롤백
                    transaction.set_rollback(True)
                    self.stdout.write(
                        self.style.WARNING('[DRY RUN 완료] 실제 변경사항은 적용되지 않았습니다.')
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS('✅ OneSquare 권한 시스템 초기화가 완료되었습니다!')
                    )
                    
        except Exception as e:
            raise CommandError(f'권한 시스템 초기화 중 오류가 발생했습니다: {str(e)}')

    def create_system_permissions(self):
        """시스템 권한 생성"""
        self.stdout.write('📋 시스템 권한 생성 중...')
        
        # CustomUser ContentType 가져오기
        user_content_type = ContentType.objects.get_for_model(CustomUser)
        
        created_count = 0
        for perm_code, perm_name in SYSTEM_PERMISSIONS.items():
            permission, created = Permission.objects.get_or_create(
                codename=perm_code,
                content_type=user_content_type,
                defaults={'name': perm_name}
            )
            
            if created:
                created_count += 1
                if not self.dry_run:
                    self.stdout.write(f'  ➕ 권한 생성: {perm_code} - {perm_name}')
            elif self.force:
                permission.name = perm_name
                if not self.dry_run:
                    permission.save()
                    self.stdout.write(f'  🔄 권한 업데이트: {perm_code} - {perm_name}')
        
        self.stdout.write(f'  ✅ 시스템 권한 {len(SYSTEM_PERMISSIONS)}개 중 {created_count}개 생성됨')

    def create_user_groups(self):
        """사용자 그룹 생성"""
        self.stdout.write('👥 사용자 그룹 생성 중...')
        
        created_groups = 0
        for user_type in UserType:
            # Django Group 생성
            group_name = f'OneSquare_{user_type.value}'
            group, group_created = Group.objects.get_or_create(
                name=group_name,
                defaults={'name': group_name}
            )
            
            if group_created:
                created_groups += 1
                if not self.dry_run:
                    self.stdout.write(f'  ➕ 그룹 생성: {group_name}')
            
            # UserGroup 확장 정보 생성
            user_group, ug_created = UserGroup.objects.get_or_create(
                group=group,
                defaults={
                    'user_type': user_type.value,
                    'description': GROUP_DESCRIPTIONS.get(user_type.value, '')
                }
            )
            
            if ug_created and not self.dry_run:
                self.stdout.write(f'  ➕ 확장 그룹 정보 생성: {user_type.label}')
            elif self.force and not self.dry_run:
                user_group.description = GROUP_DESCRIPTIONS.get(user_type.value, '')
                user_group.save()
                self.stdout.write(f'  🔄 확장 그룹 정보 업데이트: {user_type.label}')
        
        self.stdout.write(f'  ✅ 사용자 그룹 {len(UserType)}개 중 {created_groups}개 생성됨')

    def assign_group_permissions(self):
        """그룹별 권한 할당"""
        self.stdout.write('🔐 그룹별 권한 할당 중...')
        
        user_content_type = ContentType.objects.get_for_model(CustomUser)
        
        for user_type in UserType:
            group_name = f'OneSquare_{user_type.value}'
            try:
                group = Group.objects.get(name=group_name)
            except Group.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'  ❌ 그룹을 찾을 수 없음: {group_name}')
                )
                continue
            
            # 기존 권한 초기화 (force 모드인 경우)
            if self.force and not self.dry_run:
                group.permissions.clear()
            
            # 권한 매트릭스에서 해당 사용자 타입의 권한 가져오기
            user_permissions = PERMISSION_MATRIX.get(user_type.value, {})
            
            assigned_count = 0
            for module, level in user_permissions.items():
                if level == PermissionLevel.NONE:
                    continue  # 권한 없음
                
                # 모듈별 권한 할당
                permission_codes = self._get_permission_codes_for_level(module, level)
                
                for perm_code in permission_codes:
                    try:
                        permission = Permission.objects.get(
                            codename=perm_code,
                            content_type=user_content_type
                        )
                        
                        if not self.dry_run:
                            group.permissions.add(permission)
                        
                        assigned_count += 1
                        
                    except Permission.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f'  ⚠️  권한을 찾을 수 없음: {perm_code}')
                        )
            
            if not self.dry_run:
                self.stdout.write(f'  ✅ {user_type.label} 그룹에 {assigned_count}개 권한 할당')

    def _get_permission_codes_for_level(self, module, level):
        """권한 레벨에 따른 권한 코드 목록 반환"""
        base_codes = {
            SystemModule.DASHBOARD: 'dashboard',
            SystemModule.USER_MANAGEMENT: 'user_management', 
            SystemModule.REPORTS: 'reports',
            SystemModule.CALENDAR: 'calendar',
            SystemModule.FIELD_REPORTS: 'field_reports',
            SystemModule.NOTION_API: 'notion_api',
            SystemModule.SETTINGS: 'settings',
            SystemModule.ADMIN: 'admin'
        }
        
        base_code = base_codes.get(module, module.value.lower())
        
        if level == PermissionLevel.FULL:
            return [
                f'view_{base_code}',
                f'add_{base_code}', 
                f'change_{base_code}',
                f'delete_{base_code}'
            ]
        elif level == PermissionLevel.READ_WRITE:
            return [
                f'view_{base_code}',
                f'add_{base_code}',
                f'change_{base_code}'
            ]
        elif level == PermissionLevel.READ_ONLY:
            return [f'view_{base_code}']
        
        return []

    def update_existing_users(self):
        """기존 사용자들에게 그룹 할당"""
        self.stdout.write('👤 기존 사용자 그룹 할당 중...')
        
        updated_count = 0
        for user in CustomUser.objects.all():
            if self.assign_user_to_group(user) and not self.dry_run:
                updated_count += 1
        
        self.stdout.write(f'  ✅ {updated_count}명의 기존 사용자 그룹 할당 완료')

    def assign_user_to_group(self, user):
        """사용자를 해당하는 그룹에 할당"""
        group_name = f'OneSquare_{user.user_type}'
        
        try:
            group = Group.objects.get(name=group_name)
            
            # 기존 OneSquare 그룹에서 제거 (중복 방지)
            user.groups.filter(name__startswith='OneSquare_').exclude(id=group.id).delete()
            
            # 새 그룹 추가
            if not user.groups.filter(id=group.id).exists():
                if not self.dry_run:
                    user.groups.add(group)
                    self.stdout.write(f'  ➕ {user.username} → {group.name}')
                return True
                
        except Group.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'  ❌ 그룹을 찾을 수 없음: {group_name}')
            )
        
        return False


def setup_user_permissions(user):
    """개별 사용자 권한 설정 함수 (모델에서 호출)"""
    group_name = f'OneSquare_{user.user_type}'
    
    try:
        group = Group.objects.get(name=group_name)
        
        # 기존 OneSquare 그룹 제거
        user.groups.filter(name__startswith='OneSquare_').exclude(id=group.id).delete()
        
        # 새 그룹 추가
        if not user.groups.filter(id=group.id).exists():
            user.groups.add(group)
            
    except Group.DoesNotExist:
        # 그룹이 없으면 권한 시스템 초기화 필요
        from django.core.management import call_command
        call_command('setup_permissions')
        
        # 다시 시도
        try:
            group = Group.objects.get(name=group_name)
            user.groups.add(group)
        except Group.DoesNotExist:
            pass  # 실패하면 무시