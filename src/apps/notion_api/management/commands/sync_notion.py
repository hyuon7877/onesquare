"""
OneSquare Notion API 연동 - Django Management Command

Notion 데이터베이스 동기화를 위한 관리 명령어
"""

import json
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from apps.notion_api.models import NotionDatabase
from apps.notion_api.tasks import notion_scheduler, change_detector


class Command(BaseCommand):
    help = 'Notion 데이터베이스 동기화 관리'

    def add_arguments(self, parser):
        # 하위 명령어 지원
        subparsers = parser.add_subparsers(
            dest='subcommand',
            help='사용 가능한 명령어들'
        )
        
        # run: 예정된 동기화 실행
        run_parser = subparsers.add_parser(
            'run',
            help='예정된 모든 데이터베이스 동기화 실행'
        )
        run_parser.add_argument(
            '--verbose',
            action='store_true',
            help='상세한 로그 출력'
        )
        
        # sync: 특정 데이터베이스 동기화
        sync_parser = subparsers.add_parser(
            'sync',
            help='특정 데이터베이스 동기화'
        )
        sync_parser.add_argument(
            'database_id',
            type=int,
            help='동기화할 데이터베이스 ID'
        )
        sync_parser.add_argument(
            '--force',
            action='store_true',
            help='강제 동기화 (간격 무시)'
        )
        
        # status: 동기화 상태 확인
        status_parser = subparsers.add_parser(
            'status',
            help='동기화 상태 확인'
        )
        status_parser.add_argument(
            '--json',
            action='store_true',
            help='JSON 형태로 출력'
        )
        
        # detect: 변경사항 감지
        detect_parser = subparsers.add_parser(
            'detect',
            help='Notion 변경사항 감지'
        )
        detect_parser.add_argument(
            '--database-id',
            type=int,
            help='특정 데이터베이스만 확인'
        )
        
        # list: 데이터베이스 목록
        list_parser = subparsers.add_parser(
            'list',
            help='등록된 데이터베이스 목록 확인'
        )
        list_parser.add_argument(
            '--active-only',
            action='store_true',
            help='활성 데이터베이스만 표시'
        )

    def handle(self, *args, **options):
        subcommand = options.get('subcommand')
        
        if not subcommand:
            self.print_help('manage.py', 'sync_notion')
            return
        
        if subcommand == 'run':
            self.handle_run(options)
        elif subcommand == 'sync':
            self.handle_sync(options)
        elif subcommand == 'status':
            self.handle_status(options)
        elif subcommand == 'detect':
            self.handle_detect(options)
        elif subcommand == 'list':
            self.handle_list(options)
        else:
            raise CommandError(f'알 수 없는 명령어: {subcommand}')

    def handle_run(self, options):
        """예정된 동기화 실행"""
        self.stdout.write("예정된 Notion 동기화를 시작합니다...")
        
        start_time = timezone.now()
        result = notion_scheduler.run_scheduled_sync()
        end_time = timezone.now()
        
        duration = end_time - start_time
        
        # 결과 출력
        self.stdout.write(
            self.style.SUCCESS(
                f"\n동기화 완료 (소요시간: {duration.total_seconds():.1f}초)"
            )
        )
        
        self.stdout.write(f"총 데이터베이스: {result['total_databases']}")
        self.stdout.write(
            self.style.SUCCESS(f"성공: {result['successful_syncs']}")
        )
        
        if result['failed_syncs'] > 0:
            self.stdout.write(
                self.style.ERROR(f"실패: {result['failed_syncs']}")
            )
        
        if result['skipped_syncs'] > 0:
            self.stdout.write(
                self.style.WARNING(f"스킵: {result['skipped_syncs']}")
            )
        
        # 상세 정보 출력 (verbose 모드)
        if options.get('verbose'):
            self.stdout.write("\n=== 상세 결과 ===")
            for detail in result['sync_details']:
                status = "성공" if detail['success'] else ("스킵" if detail.get('skipped') else "실패")
                self.stdout.write(f"• {detail['database_title']}: {status}")
                
                if detail.get('error'):
                    self.stdout.write(
                        self.style.ERROR(f"  오류: {detail['error']}")
                    )

    def handle_sync(self, options):
        """특정 데이터베이스 동기화"""
        database_id = options['database_id']
        force = options.get('force', False)
        
        try:
            database = NotionDatabase.objects.get(id=database_id)
        except NotionDatabase.DoesNotExist:
            raise CommandError(f'데이터베이스 ID {database_id}를 찾을 수 없습니다.')
        
        if not database.is_active:
            raise CommandError(f'데이터베이스 "{database.title}"는 비활성 상태입니다.')
        
        self.stdout.write(f'데이터베이스 "{database.title}" 동기화를 시작합니다...')
        
        if force:
            # 강제 동기화 예약
            notion_scheduler.force_sync_database(database_id)
            self.stdout.write(self.style.WARNING("강제 동기화가 예약되었습니다."))
        
        # 직접 동기화 실행
        result = notion_scheduler._sync_single_database(database)
        
        if result['success']:
            self.stdout.write(
                self.style.SUCCESS(
                    f"동기화 성공! 처리된 페이지: {result['pages_processed']}개"
                )
            )
        else:
            error_msg = result.get('error', '알 수 없는 오류')
            self.stdout.write(
                self.style.ERROR(f"동기화 실패: {error_msg}")
            )

    def handle_status(self, options):
        """동기화 상태 확인"""
        summary = notion_scheduler.get_sync_status_summary()
        
        if options.get('json'):
            # JSON 형태로 출력
            self.stdout.write(json.dumps(summary, indent=2, ensure_ascii=False))
        else:
            # 사람이 읽기 쉬운 형태로 출력
            self.stdout.write("=== Notion 동기화 상태 ===\n")
            
            self.stdout.write(f"활성 데이터베이스: {summary['total_active_databases']}개")
            
            recent_stats = summary['recent_sync_stats']
            self.stdout.write(f"최근 24시간 동기화:")
            self.stdout.write(f"  총 {recent_stats['total']}회")
            self.stdout.write(
                self.style.SUCCESS(f"  완료: {recent_stats['completed']}회")
            )
            
            if recent_stats['failed'] > 0:
                self.stdout.write(
                    self.style.ERROR(f"  실패: {recent_stats['failed']}회")
                )
            
            if recent_stats['in_progress'] > 0:
                self.stdout.write(
                    self.style.WARNING(f"  진행중: {recent_stats['in_progress']}회")
                )
            
            # 데이터베이스별 상태
            self.stdout.write("\n=== 데이터베이스별 상태 ===")
            for db_status in summary['databases_status']:
                title = db_status['title']
                last_synced = db_status['last_synced']
                
                if last_synced:
                    last_sync_time = timezone.datetime.fromisoformat(last_synced).strftime('%Y-%m-%d %H:%M')
                    sync_info = f"마지막 동기화: {last_sync_time}"
                else:
                    sync_info = "동기화된 적 없음"
                
                status_icon = "⚠️" if db_status['is_sync_overdue'] else "✅"
                
                self.stdout.write(f"{status_icon} {title}")
                self.stdout.write(f"   {sync_info}")
                
                if db_status['last_sync_status']:
                    last_status = db_status['last_sync_status']
                    self.stdout.write(
                        f"   상태: {last_status['status']}, "
                        f"페이지: {last_status['total_pages']}개, "
                        f"성공률: {last_status['success_rate']:.1f}%"
                    )

    def handle_detect(self, options):
        """변경사항 감지"""
        database_id = options.get('database_id')
        
        if database_id:
            # 특정 데이터베이스만 확인
            try:
                database = NotionDatabase.objects.get(id=database_id, is_active=True)
                databases = [database]
            except NotionDatabase.DoesNotExist:
                raise CommandError(f'활성 데이터베이스 ID {database_id}를 찾을 수 없습니다.')
        else:
            # 모든 활성 데이터베이스 확인
            databases = NotionDatabase.objects.filter(is_active=True)
        
        self.stdout.write("Notion 변경사항을 감지하고 있습니다...")
        
        total_changes = 0
        
        for database in databases:
            self.stdout.write(f"\n확인 중: {database.title}")
            
            changes = change_detector.detect_database_changes(database)
            
            if changes['has_changes']:
                total_changes += 1
                self.stdout.write(self.style.WARNING(f"  변경사항 발견!"))
                
                if changes['schema_changed']:
                    self.stdout.write("  • 스키마 변경됨")
                
                if changes['pages_changed'] > 0:
                    self.stdout.write(f"  • 페이지 변경: {changes['pages_changed']}개")
                    self.stdout.write(f"    - 새 페이지: {changes['new_pages']}개")
                    self.stdout.write(f"    - 수정된 페이지: {changes['updated_pages']}개")
                
                # 강제 동기화 예약
                notion_scheduler.force_sync_database(database.id)
                self.stdout.write("  → 동기화 예약됨")
            else:
                self.stdout.write(self.style.SUCCESS("  변경사항 없음"))
        
        if total_changes > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"\n총 {total_changes}개 데이터베이스에서 변경사항이 발견되었습니다."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("\n모든 데이터베이스가 최신 상태입니다.")
            )

    def handle_list(self, options):
        """데이터베이스 목록 확인"""
        active_only = options.get('active_only', False)
        
        if active_only:
            databases = NotionDatabase.objects.filter(is_active=True)
            title = "활성 데이터베이스 목록"
        else:
            databases = NotionDatabase.objects.all()
            title = "전체 데이터베이스 목록"
        
        self.stdout.write(f"=== {title} ===\n")
        
        if not databases.exists():
            self.stdout.write("등록된 데이터베이스가 없습니다.")
            return
        
        for db in databases:
            status = "활성" if db.is_active else "비활성"
            interval = f"{db.sync_interval}초"
            
            self.stdout.write(f"ID: {db.id}")
            self.stdout.write(f"제목: {db.title}")
            self.stdout.write(f"상태: {status}")
            self.stdout.write(f"동기화 간격: {interval}")
            
            if db.last_synced:
                last_synced = db.last_synced.strftime('%Y-%m-%d %H:%M:%S')
                self.stdout.write(f"마지막 동기화: {last_synced}")
            else:
                self.stdout.write("마지막 동기화: 없음")
            
            self.stdout.write("---")