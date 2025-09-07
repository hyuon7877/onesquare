"""캘린더 캐시 워밍업 명령어"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from calendar_tasks.services import CalendarPrefetchService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '캘린더 캐시 워밍업 - 자주 사용되는 데이터 미리 로드'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            type=str,
            help='특정 사용자 username',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='모든 활성 사용자 캐시 워밍업',
        )
    
    def handle(self, *args, **options):
        self.stdout.write('캘린더 캐시 워밍업 시작...')
        
        if options['user']:
            # 특정 사용자
            try:
                user = User.objects.get(username=options['user'])
                CalendarPrefetchService.warmup_cache(user)
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {user.username} 사용자 캐시 워밍업 완료')
                )
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'✗ 사용자를 찾을 수 없습니다: {options["user"]}')
                )
        
        elif options['all']:
            # 모든 활성 사용자
            active_users = User.objects.filter(is_active=True)
            success_count = 0
            
            for user in active_users:
                try:
                    CalendarPrefetchService.warmup_cache(user)
                    success_count += 1
                    self.stdout.write(f'  • {user.username} 완료')
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'  ⚠ {user.username} 실패: {str(e)}')
                    )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✓ 총 {success_count}/{active_users.count()} 사용자 캐시 워밍업 완료'
                )
            )
        
        else:
            self.stdout.write(
                self.style.WARNING('사용법: --user USERNAME 또는 --all')
            )