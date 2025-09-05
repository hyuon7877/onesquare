#!/bin/bash

# OneSquare Notion 동기화 Cron 스크립트
# 이 스크립트는 crontab에서 주기적으로 실행됩니다

# 프로젝트 루트 디렉토리 설정
PROJECT_ROOT="/home/user/onesquare"
LOG_FILE="/home/user/onesquare/src/logs/notion_sync_cron.log"
MANAGE_PY="$PROJECT_ROOT/src/manage.py"

# 로그 디렉토리 생성
mkdir -p "$(dirname "$LOG_FILE")"

# 현재 시간 로그
echo "===========================================" >> "$LOG_FILE"
echo "Notion Sync Cron Job Started: $(date)" >> "$LOG_FILE"
echo "===========================================" >> "$LOG_FILE"

# Docker 컨테이너 내에서 실행하는 경우
if [ -f /.dockerenv ]; then
    echo "Running inside Docker container" >> "$LOG_FILE"
    cd "$PROJECT_ROOT"
    
    # Django 관리 명령어 실행
    python "$MANAGE_PY" sync_notion run --verbose >> "$LOG_FILE" 2>&1
    SYNC_EXIT_CODE=$?
    
else
    # 호스트에서 실행하는 경우 (docker-compose exec 사용)
    echo "Running from host using docker-compose" >> "$LOG_FILE"
    cd "$PROJECT_ROOT"
    
    # Docker Compose를 통해 웹 컨테이너에서 실행
    docker-compose exec -T web python manage.py sync_notion run --verbose >> "$LOG_FILE" 2>&1
    SYNC_EXIT_CODE=$?
fi

# 실행 결과 로그
if [ $SYNC_EXIT_CODE -eq 0 ]; then
    echo "Notion sync completed successfully" >> "$LOG_FILE"
else
    echo "Notion sync failed with exit code: $SYNC_EXIT_CODE" >> "$LOG_FILE"
fi

echo "Notion Sync Cron Job Ended: $(date)" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# 로그 파일이 너무 크면 회전 (최근 1000줄만 유지)
if [ -f "$LOG_FILE" ]; then
    LINE_COUNT=$(wc -l < "$LOG_FILE")
    if [ $LINE_COUNT -gt 1000 ]; then
        tail -n 800 "$LOG_FILE" > "$LOG_FILE.tmp"
        mv "$LOG_FILE.tmp" "$LOG_FILE"
        echo "Log file rotated: $(date)" >> "$LOG_FILE"
    fi
fi

exit $SYNC_EXIT_CODE