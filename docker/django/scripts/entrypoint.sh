#!/bin/bash
set -e

# 한글 환경 설정
export LANG=ko_KR.UTF-8
export LC_ALL=ko_KR.UTF-8
export PYTHONIOENCODING=utf-8

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Django 컨테이너 시작${NC}"
echo "프로젝트: $PROJECT_NAME"
echo "Python: $(python --version)"
echo "한글 설정: $LANG"
echo "시스템 시간: $(date +'%Y년 %m월 %d일 %H시 %M분 %S초')"

cd /var/www/html/$PROJECT_NAME

# 데이터베이스 연결 대기 (최대 30초)
echo "데이터베이스 연결 대기 중..."
timeout=30
counter=0
while ! mysqladmin ping -h db -P 3306 -u$DB_USER -p$DB_PASS --silent 2>/dev/null; do
    counter=$((counter+1))
    if [ $counter -gt $timeout ]; then
        echo -e "${RED}데이터베이스 연결 실패 (${timeout}초 초과)${NC}"
        exit 1
    fi
    echo -n "."
    sleep 1
done
echo -e "\n${GREEN}데이터베이스 연결 성공!${NC}"

# Django 프로젝트가 없으면 생성
if [ ! -f "manage.py" ]; then
    echo "Django 프로젝트 생성 중..."
    django-admin startproject config .
    
    # secrets.json 생성
    python /scripts/create_secrets.py
    
    # settings.py 교체
    cp /scripts/settings.py config/settings.py
    
    # urls.py 교체
    cp /scripts/urls.py config/urls.py
    
    # __init__.py 설정
    cat > config/__init__.py << 'INIT'
# -*- coding: utf-8 -*-
import pymysql
pymysql.install_as_MySQLdb()

# 버전 정보
__version__ = '1.0.0'
INIT
    
    # 기본 앱 생성
    python manage.py startapp main
    
    # main 앱의 기본 구조 생성
    mkdir -p main/templates/main
    mkdir -p main/static/main/{css,js,img}
    
    # main/apps.py 한글 설정
    cat > main/apps.py << 'APPS'
from django.apps import AppConfig

class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'
    verbose_name = '메인'
APPS
fi

# 마이그레이션
echo "마이그레이션 실행 중..."
python manage.py makemigrations
python manage.py migrate

# static 파일 수집
echo "Static 파일 수집 중..."
python manage.py collectstatic --noinput

# 디렉토리 권한 설정
mkdir -p logs staticfiles media run
chmod -R 755 logs/ staticfiles/ media/ run/

# 소켓 파일 위치 확인
rm -f run/$PROJECT_NAME.sock

# Gunicorn 실행
echo -e "${GREEN}Gunicorn 시작 (Workers: ${GUNICORN_WORKERS:-4})${NC}"
exec gunicorn config.wsgi:application \
    --name $PROJECT_NAME \
    --bind unix:run/$PROJECT_NAME.sock \
    --workers ${GUNICORN_WORKERS:-4} \
    --timeout ${GUNICORN_TIMEOUT:-300} \
    --graceful-timeout 30 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile logs/gunicorn_access.log \
    --error-logfile logs/gunicorn_error.log \
    --log-level info
