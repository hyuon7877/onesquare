"""
User group assignment management
사용자 그룹 할당 관리
"""

from django.contrib.auth.models import Group
from apps.auth_system.models import CustomUser


class UserManager:
    """사용자 관리자"""
    
    def __init__(self, command):
        self.command = command
        self.updated_count = 0
    
    def update_existing_users(self):
        """기존 사용자들에게 그룹 할당"""
        self.command.stdout.write('👤 기존 사용자 그룹 할당 중...')
        
        for user in CustomUser.objects.all():
            if self.assign_user_to_group(user):
                self.updated_count += 1
        
        self.command.stdout.write(
            f'  ✅ {self.updated_count}명의 기존 사용자 그룹 할당 완료'
        )
    
    def assign_user_to_group(self, user):
        """사용자를 해당하는 그룹에 할당"""
        group_name = f'OneSquare_{user.user_type}'
        
        try:
            group = Group.objects.get(name=group_name)
            
            # 기존 OneSquare 그룹에서 제거 (중복 방지)
            self._remove_old_groups(user, group)
            
            # 새 그룹 추가
            return self._add_to_group(user, group)
                
        except Group.DoesNotExist:
            self.command.stdout.write(
                self.command.style.ERROR(f'  ❌ 그룹을 찾을 수 없음: {group_name}')
            )
            return False
    
    def _remove_old_groups(self, user, current_group):
        """기존 OneSquare 그룹 제거"""
        old_groups = user.groups.filter(
            name__startswith='OneSquare_'
        ).exclude(id=current_group.id)
        
        if not self.command.dry_run:
            old_groups.delete()
    
    def _add_to_group(self, user, group):
        """사용자를 그룹에 추가"""
        if not user.groups.filter(id=group.id).exists():
            if not self.command.dry_run:
                user.groups.add(group)
                self.command.stdout.write(f'  ➕ {user.username} → {group.name}')
            return True
        return False


def setup_user_permissions(user):
    """개별 사용자 권한 설정 (외부 호출용)"""
    group_name = f'OneSquare_{user.user_type}'
    
    try:
        group = Group.objects.get(name=group_name)
        
        # 기존 OneSquare 그룹 제거
        user.groups.filter(
            name__startswith='OneSquare_'
        ).exclude(id=group.id).delete()
        
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
            pass  # 권한 시스템 초기화 실패