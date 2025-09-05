"""
OneSquare Dashboard - Notion 변경사항 폴링 명령어
주기적으로 Notion API를 체크하고 알림 생성
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
import time
import signal
import sys
from apps.dashboard.notion_notification_service import NotionChangePoller


class Command(BaseCommand):
    help = 'Notion 변경사항을 주기적으로 체크하고 알림 생성'
    
    def __init__(self):
        super().__init__()
        self.poller = NotionChangePoller()
        self.running = True
        
        # 신호 처리 (Ctrl+C로 종료)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=300,
            help='폴링 간격(초, 기본값: 300초/5분)'
        )
        
        parser.add_argument(
            '--once',
            action='store_true',
            help='한번만 실행하고 종료'
        )
        
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='오래된 알림 정리도 함께 실행'
        )
    
    def handle(self, *args, **options):
        interval = options['interval']
        run_once = options['once']
        cleanup = options['cleanup']
        
        self.stdout.write(
            self.style.SUCCESS('🚀 Notion 변경사항 폴링 서비스를 시작합니다...')
        )
        
        if run_once:
            self.stdout.write('📝 단일 실행 모드')
        else:
            self.stdout.write(f'🔄 주기적 실행 모드 (간격: {interval}초)')
        
        try:
            if run_once:
                self._run_single_cycle(cleanup)
            else:
                self._run_continuous_polling(interval, cleanup)
                
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('\n⏹️  사용자에 의해 중단되었습니다.')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 오류가 발생했습니다: {str(e)}')
            )
        finally:
            self.stdout.write(
                self.style.SUCCESS('✅ Notion 폴링 서비스가 종료되었습니다.')
            )
    
    def _run_single_cycle(self, cleanup=False):
        """단일 폴링 사이클 실행"""
        self.stdout.write('🔍 Notion 변경사항 확인 중...')
        
        start_time = timezone.now()
        self.poller.run_polling_cycle()
        end_time = timezone.now()
        
        duration = (end_time - start_time).total_seconds()
        self.stdout.write(
            self.style.SUCCESS(f'✅ 폴링 완료 (소요시간: {duration:.2f}초)')
        )
        
        if cleanup:
            self._run_cleanup()
    
    def _run_continuous_polling(self, interval, cleanup=False):
        """연속 폴링 실행"""
        cycle_count = 0
        
        while self.running:
            cycle_count += 1
            self.stdout.write(
                f'\n📊 폴링 사이클 #{cycle_count} ({timezone.now().strftime("%Y-%m-%d %H:%M:%S")})'
            )
            
            try:
                start_time = timezone.now()
                self.poller.run_polling_cycle()
                end_time = timezone.now()
                
                duration = (end_time - start_time).total_seconds()
                self.stdout.write(
                    self.style.SUCCESS(f'✅ 사이클 완료 (소요시간: {duration:.2f}초)')
                )
                
                # 매 시간마다 정리 작업 실행
                if cleanup and cycle_count % 12 == 0:  # 12 사이클(1시간)마다
                    self._run_cleanup()
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ 사이클 #{cycle_count} 오류: {str(e)}')
                )
            
            # 다음 사이클까지 대기
            if self.running:
                self.stdout.write(f'⏳ {interval}초 대기 중... (Ctrl+C로 종료)')
                
                # 인터럽트 가능한 sleep
                for _ in range(interval):
                    if not self.running:
                        break
                    time.sleep(1)
    
    def _run_cleanup(self):
        """알림 정리 작업"""
        self.stdout.write('🧹 오래된 알림 정리 중...')
        
        from apps.dashboard.notion_notification_service import NotionNotificationService
        notification_service = NotionNotificationService()
        
        deleted_count = notification_service.cleanup_old_notifications(days=30)
        self.stdout.write(
            self.style.SUCCESS(f'🗑️  {deleted_count}개 알림 정리 완료')
        )
    
    def _signal_handler(self, signum, frame):
        """신호 처리 핸들러"""
        self.stdout.write(
            self.style.WARNING(f'\n⚠️  신호 {signum} 수신, 종료 준비 중...')
        )
        self.running = False