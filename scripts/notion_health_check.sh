#!/bin/bash

# OneSquare Notion 건강성 검사 Cron 스크립트
# 시스템 상태를 모니터링하고 문제 발생 시 알림을 발송합니다

# 프로젝트 루트 디렉토리 설정
PROJECT_ROOT="/home/user/onesquare"
LOG_FILE="/home/user/onesquare/src/logs/notion_health_check.log"
MANAGE_PY="$PROJECT_ROOT/src/manage.py"

# 로그 디렉토리 생성
mkdir -p "$(dirname "$LOG_FILE")"

# 현재 시간 로그
echo "===========================================" >> "$LOG_FILE"
echo "Notion Health Check Started: $(date)" >> "$LOG_FILE"
echo "===========================================" >> "$LOG_FILE"

# Python 스크립트로 건강성 검사 실행
PYTHON_SCRIPT="
import os, sys, django
sys.path.append('/home/user/onesquare/src')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.notion_api.monitoring import run_health_check
import json

try:
    health_report = run_health_check()
    print('Health check completed successfully')
    print(f'Overall status: {health_report[\"overall_status\"]}')
    print(f'Active databases: {health_report[\"statistics\"][\"active_databases\"]}')
    print(f'24h success rate: {health_report[\"statistics\"][\"overall_success_rate\"]:.1f}%')
    
    if health_report['issues']:
        print('Issues found:')
        for issue in health_report['issues']:
            print(f'  - {issue}')
    
    if health_report['warnings']:
        print('Warnings:')
        for warning in health_report['warnings']:
            print(f'  - {warning}')
    
except Exception as e:
    print(f'Health check failed: {str(e)}')
    sys.exit(1)
"

# Docker 컨테이너 내에서 실행하는 경우
if [ -f /.dockerenv ]; then
    echo "Running health check inside Docker container" >> "$LOG_FILE"
    cd "$PROJECT_ROOT"
    
    python -c "$PYTHON_SCRIPT" >> "$LOG_FILE" 2>&1
    CHECK_EXIT_CODE=$?
    
else
    # 호스트에서 실행하는 경우 (docker-compose exec 사용)
    echo "Running health check from host using docker-compose" >> "$LOG_FILE"
    cd "$PROJECT_ROOT"
    
    echo "$PYTHON_SCRIPT" | docker-compose exec -T web python >> "$LOG_FILE" 2>&1
    CHECK_EXIT_CODE=$?
fi

# 실행 결과 로그
if [ $CHECK_EXIT_CODE -eq 0 ]; then
    echo "Health check completed successfully" >> "$LOG_FILE"
else
    echo "Health check failed with exit code: $CHECK_EXIT_CODE" >> "$LOG_FILE"
fi

echo "Notion Health Check Ended: $(date)" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# 로그 파일이 너무 크면 회전 (최근 500줄만 유지)
if [ -f "$LOG_FILE" ]; then
    LINE_COUNT=$(wc -l < "$LOG_FILE")
    if [ $LINE_COUNT -gt 500 ]; then
        tail -n 400 "$LOG_FILE" > "$LOG_FILE.tmp"
        mv "$LOG_FILE.tmp" "$LOG_FILE"
        echo "Health check log file rotated: $(date)" >> "$LOG_FILE"
    fi
fi

exit $CHECK_EXIT_CODE