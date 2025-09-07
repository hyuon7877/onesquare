"""시스템 상태 체크 명령어"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import psutil
import os
import json
from datetime import datetime


class Command(BaseCommand):
    help = '시스템 상태 종합 체크'

    def handle(self, *args, **options):
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('시스템 상태 점검 시작')
        self.stdout.write('=' * 60 + '\n')
        
        # 1. 데이터베이스 상태
        self.check_database()
        
        # 2. 캐시 상태
        self.check_cache()
        
        # 3. 시스템 리소스
        self.check_system_resources()
        
        # 4. Django 설정
        self.check_django_settings()
        
        # 5. 로그 파일
        self.check_log_files()
        
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('시스템 점검 완료'))
        self.stdout.write('=' * 60 + '\n')
    
    def check_database(self):
        """데이터베이스 연결 상태 확인"""
        self.stdout.write('\n[데이터베이스 상태]')
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
                # 테이블 수 확인
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE()
                """)
                table_count = cursor.fetchone()[0]
                
            self.stdout.write(self.style.SUCCESS(
                f"✓ 데이터베이스 연결: 정상"
            ))
            self.stdout.write(f"  - 테이블 수: {table_count}")
            
            # 마이그레이션 상태
            from django.core.management import call_command
            from io import StringIO
            out = StringIO()
            call_command('showmigrations', '--plan', stdout=out, verbosity=0)
            migrations = out.getvalue()
            pending = migrations.count('[ ]')
            applied = migrations.count('[X]')
            
            self.stdout.write(f"  - 적용된 마이그레이션: {applied}")
            if pending > 0:
                self.stdout.write(self.style.WARNING(
                    f"  - 대기 중인 마이그레이션: {pending}"
                ))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f"✗ 데이터베이스 연결 실패: {str(e)}"
            ))
    
    def check_cache(self):
        """캐시 상태 확인"""
        self.stdout.write('\n[캐시 상태]')
        try:
            cache.set('health_check', 'ok', 1)
            value = cache.get('health_check')
            
            if value == 'ok':
                self.stdout.write(self.style.SUCCESS("✓ 캐시 연결: 정상"))
                
                # 캐시 통계
                if hasattr(cache, '_cache'):
                    stats = cache._cache.get_stats()
                    if stats:
                        self.stdout.write(f"  - 캐시 항목 수: {stats.get('curr_items', 'N/A')}")
                        self.stdout.write(f"  - 캐시 히트율: {stats.get('hit_rate', 'N/A')}%")
            else:
                self.stdout.write(self.style.WARNING("⚠ 캐시 연결: 제한적"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f"✗ 캐시 연결 실패: {str(e)}"
            ))
    
    def check_system_resources(self):
        """시스템 리소스 상태 확인"""
        self.stdout.write('\n[시스템 리소스]')
        
        # CPU 사용률
        cpu_percent = psutil.cpu_percent(interval=1)
        status = self.style.SUCCESS("✓") if cpu_percent < 80 else self.style.WARNING("⚠")
        self.stdout.write(f"{status} CPU 사용률: {cpu_percent}%")
        
        # 메모리 사용률
        memory = psutil.virtual_memory()
        mem_percent = memory.percent
        status = self.style.SUCCESS("✓") if mem_percent < 80 else self.style.WARNING("⚠")
        self.stdout.write(f"{status} 메모리 사용률: {mem_percent}% "
                         f"({memory.used / 1024**3:.1f}GB / {memory.total / 1024**3:.1f}GB)")
        
        # 디스크 사용률
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        status = self.style.SUCCESS("✓") if disk_percent < 80 else self.style.WARNING("⚠")
        self.stdout.write(f"{status} 디스크 사용률: {disk_percent}% "
                         f"({disk.used / 1024**3:.1f}GB / {disk.total / 1024**3:.1f}GB)")
        
        # Python 프로세스 정보
        process = psutil.Process(os.getpid())
        self.stdout.write(f"\n[현재 프로세스]")
        self.stdout.write(f"  - PID: {process.pid}")
        self.stdout.write(f"  - 메모리 사용: {process.memory_info().rss / 1024**2:.1f}MB")
        self.stdout.write(f"  - 스레드 수: {process.num_threads()}")
        self.stdout.write(f"  - 열린 파일 수: {len(process.open_files())}")
    
    def check_django_settings(self):
        """Django 설정 확인"""
        self.stdout.write('\n[Django 설정]')
        
        # 중요 설정 확인
        self.stdout.write(f"  - DEBUG: {settings.DEBUG}")
        self.stdout.write(f"  - ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
        self.stdout.write(f"  - TIME_ZONE: {settings.TIME_ZONE}")
        self.stdout.write(f"  - USE_TZ: {settings.USE_TZ}")
        
        # 보안 설정
        self.stdout.write("\n[보안 설정]")
        security_checks = {
            'SECURE_SSL_REDIRECT': getattr(settings, 'SECURE_SSL_REDIRECT', False),
            'SESSION_COOKIE_SECURE': getattr(settings, 'SESSION_COOKIE_SECURE', False),
            'CSRF_COOKIE_SECURE': getattr(settings, 'CSRF_COOKIE_SECURE', False),
            'X_FRAME_OPTIONS': getattr(settings, 'X_FRAME_OPTIONS', None),
        }
        
        for setting, value in security_checks.items():
            if settings.DEBUG:
                self.stdout.write(f"  - {setting}: {value} (개발 모드)")
            else:
                status = self.style.SUCCESS("✓") if value else self.style.WARNING("⚠")
                self.stdout.write(f"{status} {setting}: {value}")
    
    def check_log_files(self):
        """로그 파일 상태 확인"""
        self.stdout.write('\n[로그 파일]')
        
        log_dir = os.path.join(settings.BASE_DIR, 'logs')
        
        if os.path.exists(log_dir):
            log_files = os.listdir(log_dir)
            self.stdout.write(f"  - 로그 디렉토리: {log_dir}")
            self.stdout.write(f"  - 로그 파일 수: {len(log_files)}")
            
            # 각 로그 파일 크기
            total_size = 0
            for log_file in log_files:
                file_path = os.path.join(log_dir, log_file)
                if os.path.isfile(file_path):
                    size = os.path.getsize(file_path)
                    total_size += size
                    self.stdout.write(f"    • {log_file}: {size / 1024:.1f}KB")
            
            self.stdout.write(f"  - 총 로그 크기: {total_size / 1024**2:.1f}MB")
        else:
            self.stdout.write(self.style.WARNING("⚠ 로그 디렉토리가 존재하지 않습니다"))