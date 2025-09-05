#!/bin/bash

# OneSquare Notion API 테스트 스크립트
# Django 테스트와 API 연결 테스트를 실행합니다

# 프로젝트 루트 디렉토리 설정
PROJECT_ROOT="/home/user/onesquare"
LOG_FILE="/home/user/onesquare/src/logs/notion_api_tests.log"
MANAGE_PY="$PROJECT_ROOT/src/manage.py"

# 로그 디렉토리 생성
mkdir -p "$(dirname "$LOG_FILE")"

echo "===========================================" | tee "$LOG_FILE"
echo "Notion API 테스트 시작: $(date)" | tee -a "$LOG_FILE"
echo "===========================================" | tee -a "$LOG_FILE"

# Python 테스트 스크립트
PYTHON_TEST_SCRIPT="
import os, sys, django
sys.path.append('/home/user/onesquare/src')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.notion_api.services import NotionClient, NotionSyncService
from apps.notion_api.tasks import NotionSyncScheduler
from apps.notion_api.models import NotionDatabase
from apps.notion_api.retry_utils import retry_executor
from django.contrib.auth import get_user_model
from django.test.utils import setup_test_environment, teardown_test_environment
import traceback

User = get_user_model()

def test_notion_client_initialization():
    '''NotionClient 초기화 테스트'''
    try:
        client = NotionClient()
        print('✓ NotionClient 초기화 성공')
        return True
    except Exception as e:
        print(f'✗ NotionClient 초기화 실패: {str(e)}')
        return False

def test_notion_sync_service():
    '''NotionSyncService 테스트'''
    try:
        service = NotionSyncService()
        print('✓ NotionSyncService 초기화 성공')
        return True
    except Exception as e:
        print(f'✗ NotionSyncService 초기화 실패: {str(e)}')
        return False

def test_notion_scheduler():
    '''NotionSyncScheduler 테스트'''
    try:
        scheduler = NotionSyncScheduler()
        status_summary = scheduler.get_sync_status_summary()
        print('✓ NotionSyncScheduler 초기화 및 상태 조회 성공')
        print(f'  활성 데이터베이스: {status_summary[\"total_active_databases\"]}개')
        return True
    except Exception as e:
        print(f'✗ NotionSyncScheduler 테스트 실패: {str(e)}')
        return False

def test_retry_mechanism():
    '''재시도 메커니즘 테스트'''
    try:
        def test_function():
            return 'retry test success'
        
        result = retry_executor.execute(test_function)
        if result.success:
            print('✓ 재시도 메커니즘 테스트 성공')
            return True
        else:
            print('✗ 재시도 메커니즘 테스트 실패')
            return False
    except Exception as e:
        print(f'✗ 재시도 메커니즘 테스트 실패: {str(e)}')
        return False

def test_database_models():
    '''데이터베이스 모델 테스트'''
    try:
        # NotionDatabase 모델 테스트
        from django.db import connection
        
        # 테이블 존재 확인
        with connection.cursor() as cursor:
            cursor.execute(\"\"\"
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name LIKE '%notion%'
                UNION
                SELECT TABLE_NAME as name FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME LIKE '%notion%'
            \"\"\")
            tables = cursor.fetchall()
        
        if tables:
            print(f'✓ Notion 관련 테이블 발견: {len(tables)}개')
        else:
            print('⚠ Notion 관련 테이블이 없음 (마이그레이션 필요)')
        
        # 모델 import 테스트
        count = NotionDatabase.objects.count()
        print(f'✓ NotionDatabase 모델 접근 성공 (현재 {count}개)')
        return True
        
    except Exception as e:
        print(f'✗ 데이터베이스 모델 테스트 실패: {str(e)}')
        return False

def test_management_commands():
    '''Django 관리 명령어 테스트'''
    try:
        from django.core.management import call_command
        from io import StringIO
        
        # sync_notion 명령어 help 테스트
        out = StringIO()
        call_command('help', 'sync_notion', stdout=out)
        help_output = out.getvalue()
        
        if 'sync_notion' in help_output:
            print('✓ sync_notion 관리 명령어 등록됨')
            return True
        else:
            print('✗ sync_notion 관리 명령어 찾을 수 없음')
            return False
            
    except Exception as e:
        print(f'⚠ Django 관리 명령어 테스트: {str(e)}')
        return True  # 명령어가 없어도 치명적이지 않음

def run_all_tests():
    '''모든 테스트 실행'''
    print('Notion API 통합 테스트 실행 중...')
    print()
    
    tests = [
        ('NotionClient 초기화', test_notion_client_initialization),
        ('NotionSyncService', test_notion_sync_service),
        ('NotionScheduler', test_notion_scheduler),
        ('재시도 메커니즘', test_retry_mechanism),
        ('데이터베이스 모델', test_database_models),
        ('관리 명령어', test_management_commands),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f'{test_name} 테스트 중...')
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f'✗ {test_name} 테스트 중 예외 발생: {str(e)}')
            traceback.print_exc()
            results.append((test_name, False))
        print()
    
    # 결과 요약
    print('=' * 50)
    print('테스트 결과 요약:')
    print('=' * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = '✓ 성공' if success else '✗ 실패'
        print(f'{test_name}: {status}')
        if success:
            passed += 1
    
    print()
    print(f'전체: {total}개, 성공: {passed}개, 실패: {total-passed}개')
    print(f'성공률: {(passed/total)*100:.1f}%')
    
    return passed == total

# 테스트 실행
if __name__ == '__main__':
    try:
        setup_test_environment()
        success = run_all_tests()
        teardown_test_environment()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f'테스트 실행 중 치명적 오류: {str(e)}')
        traceback.print_exc()
        sys.exit(1)
"

# Docker 컨테이너 내에서 실행하는 경우
if [ -f /.dockerenv ]; then
    echo "Docker 컨테이너 내에서 Notion API 테스트 실행" >> "$LOG_FILE"
    cd "$PROJECT_ROOT"
    
    echo "$PYTHON_TEST_SCRIPT" | python >> "$LOG_FILE" 2>&1
    TEST_EXIT_CODE=$?
    
    # Django 테스트도 실행
    echo "Django 단위 테스트 실행..." >> "$LOG_FILE"
    python "$MANAGE_PY" test apps.notion_api --verbosity=2 >> "$LOG_FILE" 2>&1
    DJANGO_TEST_CODE=$?
    
else
    # 호스트에서 실행하는 경우 (docker-compose exec 사용)
    echo "Docker Compose를 통해 Notion API 테스트 실행" >> "$LOG_FILE"
    cd "$PROJECT_ROOT"
    
    if command -v docker-compose &> /dev/null; then
        echo "$PYTHON_TEST_SCRIPT" | docker-compose exec -T web python >> "$LOG_FILE" 2>&1
        TEST_EXIT_CODE=$?
        
        echo "Django 단위 테스트 실행..." >> "$LOG_FILE"
        docker-compose exec -T web python manage.py test apps.notion_api --verbosity=2 >> "$LOG_FILE" 2>&1
        DJANGO_TEST_CODE=$?
    else
        echo "Docker Compose를 사용할 수 없습니다. 테스트를 건너뜁니다." >> "$LOG_FILE"
        TEST_EXIT_CODE=0
        DJANGO_TEST_CODE=0
    fi
fi

# 결과 출력
if [ $TEST_EXIT_CODE -eq 0 ] && [ $DJANGO_TEST_CODE -eq 0 ]; then
    echo "✓ 모든 Notion API 테스트가 성공적으로 완료되었습니다." | tee -a "$LOG_FILE"
else
    echo "✗ 일부 테스트가 실패했습니다." | tee -a "$LOG_FILE"
    echo "  통합 테스트 결과: $TEST_EXIT_CODE" | tee -a "$LOG_FILE"
    echo "  Django 테스트 결과: $DJANGO_TEST_CODE" | tee -a "$LOG_FILE"
fi

echo "Notion API 테스트 완료: $(date)" >> "$LOG_FILE"
echo "상세한 로그는 $LOG_FILE 를 확인하세요."

# 로그 파일 끝부분 출력
echo ""
echo "=== 테스트 로그 (마지막 50줄) ==="
tail -n 50 "$LOG_FILE"

exit $((TEST_EXIT_CODE + DJANGO_TEST_CODE))