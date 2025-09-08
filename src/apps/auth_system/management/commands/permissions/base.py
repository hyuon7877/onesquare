"""
Base class for permission setup
권한 설정 기본 클래스
"""

from django.core.management.base import BaseCommand
from django.db import transaction


class PermissionSetupBase(BaseCommand):
    """권한 설정 기본 클래스"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dry_run = False
        self.force = False
        self.created_count = 0
        self.updated_count = 0
        
    def add_arguments(self, parser):
        """커맨드 인자 추가"""
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
    
    def setup_options(self, options):
        """옵션 설정"""
        self.dry_run = options.get('dry_run', False)
        self.force = options.get('force', False)
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('[DRY RUN] 실제 변경 없이 실행 계획을 출력합니다.')
            )
    
    def log_action(self, action, message, style='SUCCESS'):
        """액션 로그 출력"""
        if not self.dry_run:
            style_func = getattr(self.style, style)
            self.stdout.write(f'  {action} {style_func(message)}')
    
    def log_summary(self, title, total, created, updated=0):
        """요약 로그 출력"""
        summary = f'  ✅ {title}: 전체 {total}개'
        if created > 0:
            summary += f', 생성 {created}개'
        if updated > 0:
            summary += f', 업데이트 {updated}개'
        self.stdout.write(self.style.SUCCESS(summary))