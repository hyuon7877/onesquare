"""
OneSquare 권한 시스템 초기화 Management Command (리팩토링 버전)
"""

from django.core.management.base import CommandError
from django.db import transaction
from .permissions import (
    PermissionSetupBase,
    GroupManager,
    PermissionManager,
    UserManager
)


class Command(PermissionSetupBase):
    """권한 시스템 초기화 커맨드"""
    
    help = 'OneSquare 권한 시스템을 초기화합니다. Groups, Permissions, UserGroups를 생성합니다.'
    
    def handle(self, *args, **options):
        """권한 시스템 초기화 실행"""
        self.setup_options(options)
        
        try:
            with transaction.atomic():
                # 매니저 초기화
                permission_manager = PermissionManager(self)
                group_manager = GroupManager(self, permission_manager)
                user_manager = UserManager(self)
                
                # 권한 시스템 초기화
                permission_manager.create_system_permissions()
                group_manager.create_user_groups()
                group_manager.assign_group_permissions()
                user_manager.update_existing_users()
                
                # Dry run 처리
                if self.dry_run:
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