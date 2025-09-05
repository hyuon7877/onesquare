"""
로그 파일 정리 및 데이터베이스 로그 정리 명령어
정기적으로 실행하여 로그 용량을 관리합니다.
"""
import os
import glob
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.monitoring.models import (
    SystemMetrics, RequestMetrics, UserActivity, 
    NotionAPIMetrics, ErrorLog, PerformanceAlert
)


logger = logging.getLogger('monitoring')


class Command(BaseCommand):
    help = '로그 파일 및 모니터링 데이터 정리'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='보관할 일수 (기본: 30일)'
        )
        parser.add_argument(
            '--log-files',
            action='store_true',
            help='로그 파일도 함께 정리'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 삭제하지 않고 삭제할 데이터만 표시'
        )
        parser.add_argument(
            '--compress',
            action='store_true',
            help='삭제 전 로그 파일 압축'
        )
    
    def handle(self, *args, **options):
        days_to_keep = options['days']
        cleanup_files = options['log_files']
        dry_run = options['dry_run']
        compress_files = options['compress']
        
        self.stdout.write(
            self.style.SUCCESS(f'로그 정리 시작 - {days_to_keep}일 이전 데이터 정리')
        )
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN 모드 - 실제 삭제하지 않음'))
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # 1. 데이터베이스 로그 정리
        self.cleanup_database_logs(cutoff_date, dry_run)
        
        # 2. 로그 파일 정리 (옵션)
        if cleanup_files:
            self.cleanup_log_files(cutoff_date, dry_run, compress_files)
        
        self.stdout.write(self.style.SUCCESS('로그 정리 완료'))
    
    def cleanup_database_logs(self, cutoff_date, dry_run):
        """데이터베이스 로그 정리"""
        self.stdout.write('데이터베이스 로그 정리 중...')
        
        # SystemMetrics 정리 (30일 이전)
        system_metrics_count = SystemMetrics.objects.filter(
            timestamp__lt=cutoff_date
        ).count()
        
        if system_metrics_count > 0:
            self.stdout.write(f'  - SystemMetrics: {system_metrics_count}개 레코드')
            if not dry_run:
                SystemMetrics.objects.filter(timestamp__lt=cutoff_date).delete()
        
        # RequestMetrics 정리 (15일 이전은 요약된 데이터만 보관)
        request_cutoff = datetime.now() - timedelta(days=min(15, cutoff_date.day))
        request_metrics_count = RequestMetrics.objects.filter(
            timestamp__lt=request_cutoff
        ).count()
        
        if request_metrics_count > 0:
            self.stdout.write(f'  - RequestMetrics: {request_metrics_count}개 레코드')
            if not dry_run:
                RequestMetrics.objects.filter(timestamp__lt=request_cutoff).delete()
        
        # UserActivity 정리 (7일 이전은 익명 사용자 활동만 정리)
        activity_cutoff = datetime.now() - timedelta(days=7)
        anonymous_activity_count = UserActivity.objects.filter(
            timestamp__lt=activity_cutoff,
            is_authenticated=False
        ).count()
        
        if anonymous_activity_count > 0:
            self.stdout.write(f'  - Anonymous UserActivity: {anonymous_activity_count}개 레코드')
            if not dry_run:
                UserActivity.objects.filter(
                    timestamp__lt=activity_cutoff,
                    is_authenticated=False
                ).delete()
        
        # NotionAPIMetrics 정리
        notion_metrics_count = NotionAPIMetrics.objects.filter(
            timestamp__lt=cutoff_date
        ).count()
        
        if notion_metrics_count > 0:
            self.stdout.write(f'  - NotionAPIMetrics: {notion_metrics_count}개 레코드')
            if not dry_run:
                NotionAPIMetrics.objects.filter(timestamp__lt=cutoff_date).delete()
        
        # ErrorLog 정리 (해결된 에러만)
        resolved_errors_count = ErrorLog.objects.filter(
            timestamp__lt=cutoff_date,
            is_resolved=True
        ).count()
        
        if resolved_errors_count > 0:
            self.stdout.write(f'  - Resolved ErrorLog: {resolved_errors_count}개 레코드')
            if not dry_run:
                ErrorLog.objects.filter(
                    timestamp__lt=cutoff_date,
                    is_resolved=True
                ).delete()
        
        # PerformanceAlert 정리 (확인된 알림만)
        acknowledged_alerts_count = PerformanceAlert.objects.filter(
            timestamp__lt=cutoff_date,
            is_acknowledged=True
        ).count()
        
        if acknowledged_alerts_count > 0:
            self.stdout.write(f'  - Acknowledged PerformanceAlert: {acknowledged_alerts_count}개 레코드')
            if not dry_run:
                PerformanceAlert.objects.filter(
                    timestamp__lt=cutoff_date,
                    is_acknowledged=True
                ).delete()
    
    def cleanup_log_files(self, cutoff_date, dry_run, compress_files):
        """로그 파일 정리"""
        self.stdout.write('로그 파일 정리 중...')
        
        # 로그 디렉토리 경로
        log_dir = getattr(settings, 'LOG_DIR', '/home/user/onesquare/src/logs')
        
        if not os.path.exists(log_dir):
            self.stdout.write(self.style.WARNING(f'로그 디렉토리가 존재하지 않습니다: {log_dir}'))
            return
        
        # 로그 파일 패턴들
        log_patterns = [
            '*.log',
            '*.log.*',
            'django_*.log',
            'gunicorn_*.log',
            'error_*.log',
            'access_*.log'
        ]
        
        for pattern in log_patterns:
            log_files = glob.glob(os.path.join(log_dir, pattern))
            
            for log_file in log_files:
                try:
                    # 파일 수정 시간 확인
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
                    
                    if file_mtime < cutoff_date:
                        file_size = os.path.getsize(log_file) / (1024 * 1024)  # MB
                        self.stdout.write(f'  - {log_file} ({file_size:.2f}MB)')
                        
                        if not dry_run:
                            if compress_files and not log_file.endswith('.gz'):
                                # 압축 후 삭제
                                self.compress_log_file(log_file)
                            else:
                                # 직접 삭제
                                os.remove(log_file)
                                
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'파일 처리 중 오류: {log_file} - {str(e)}')
                    )
    
    def compress_log_file(self, log_file):
        """로그 파일 압축"""
        import gzip
        import shutil
        
        compressed_file = f'{log_file}.gz'
        
        try:
            with open(log_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # 원본 파일 삭제
            os.remove(log_file)
            
            self.stdout.write(f'    압축 완료: {compressed_file}')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'압축 실패 {log_file}: {str(e)}')
            )
    
    def get_directory_size(self, directory):
        """디렉토리 크기 계산"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        except Exception as e:
            logger.error(f'Directory size calculation error: {str(e)}')
        
        return total_size / (1024 * 1024)  # MB