#!/bin/bash

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 프로젝트 이름 입력
if [ -z "$1" ]; then
    read -p "초기화할 프로젝트 이름을 입력하세요: " PROJECT_NAME
else
    PROJECT_NAME=$1
fi

echo -e "${YELLOW}[WARNING]${NC} '$PROJECT_NAME' 프로젝트를 완전히 초기화합니다."
echo -e "${YELLOW}[WARNING]${NC} 모든 데이터가 삭제됩니다!"
read -p "정말 계속하시겠습니까? [y/N]: " CONFIRM

if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    echo -e "${BLUE}[INFO]${NC} 취소되었습니다."
    exit 0
fi

echo -e "${BLUE}[INFO]${NC} 프로젝트 초기화 시작..."

# 1. 프로젝트 디렉토리 확인
if [ -d "$HOME/$PROJECT_NAME" ]; then
    cd "$HOME/$PROJECT_NAME"
    
    # Docker Compose 정리
    if [ -f "docker-compose.yml" ]; then
        echo -e "${BLUE}[INFO]${NC} Docker 컨테이너, 볼륨, 네트워크 제거 중..."
        
        # docker compose 또는 docker-compose 명령 확인
        if command -v docker-compose &> /dev/null; then
            COMPOSE_CMD="docker-compose"
        else
            COMPOSE_CMD="docker compose"
        fi
        
        # .env 파일 존재 확인
        if [ -f ".env" ]; then
            $COMPOSE_CMD --env-file .env down -v --remove-orphans 2>/dev/null || true
        else
            $COMPOSE_CMD down -v --remove-orphans 2>/dev/null || true
        fi
    fi
    
    # 상위 디렉토리로 이동
    cd ..
else
    echo -e "${YELLOW}[WARNING]${NC} 프로젝트 디렉토리가 없습니다: $HOME/$PROJECT_NAME"
fi

# 2. Docker 리소스 정리
echo -e "${BLUE}[INFO]${NC} Docker 리소스 정리 중..."

# 컨테이너 제거
CONTAINERS=$(docker ps -a -q --filter "name=${PROJECT_NAME}")
if [ ! -z "$CONTAINERS" ]; then
    echo "  - 컨테이너 제거 중..."
    docker rm -f $CONTAINERS 2>/dev/null || true
fi

# 이미지 제거
IMAGES=$(docker images -q "${PROJECT_NAME}*")
if [ ! -z "$IMAGES" ]; then
    echo "  - 이미지 제거 중..."
    docker rmi -f $IMAGES 2>/dev/null || true
fi

# 볼륨 제거
VOLUMES=$(docker volume ls -q | grep "${PROJECT_NAME}")
if [ ! -z "$VOLUMES" ]; then
    echo "  - 볼륨 제거 중..."
    docker volume rm $VOLUMES 2>/dev/null || true
fi

# 네트워크 제거
NETWORKS=$(docker network ls -q --filter "name=${PROJECT_NAME}")
if [ ! -z "$NETWORKS" ]; then
    echo "  - 네트워크 제거 중..."
    docker network rm $NETWORKS 2>/dev/null || true
fi

# 3. 프로젝트 디렉토리 삭제
if [ -d "$HOME/$PROJECT_NAME" ]; then
    echo -e "${BLUE}[INFO]${NC} 프로젝트 디렉토리 삭제 중..."
    rm -rf "$HOME/$PROJECT_NAME"
fi

# 4. 정리 결과 확인
echo -e "${BLUE}[INFO]${NC} 정리 결과 확인 중..."

# 남은 리소스 확인
REMAINING_CONTAINERS=$(docker ps -a | grep "$PROJECT_NAME" | wc -l)
REMAINING_IMAGES=$(docker images | grep "$PROJECT_NAME" | wc -l)
REMAINING_VOLUMES=$(docker volume ls | grep "$PROJECT_NAME" | wc -l)
REMAINING_NETWORKS=$(docker network ls | grep "$PROJECT_NAME" | wc -l)

if [ $REMAINING_CONTAINERS -eq 0 ] && [ $REMAINING_IMAGES -eq 0 ] && \
   [ $REMAINING_VOLUMES -eq 0 ] && [ $REMAINING_NETWORKS -eq 0 ]; then
    echo -e "${GREEN}[SUCCESS]${NC} '$PROJECT_NAME' 프로젝트가 완전히 초기화되었습니다!"
else
    echo -e "${YELLOW}[WARNING]${NC} 일부 리소스가 남아있을 수 있습니다:"
    [ $REMAINING_CONTAINERS -gt 0 ] && echo "  - 컨테이너: $REMAINING_CONTAINERS개"
    [ $REMAINING_IMAGES -gt 0 ] && echo "  - 이미지: $REMAINING_IMAGES개"
    [ $REMAINING_VOLUMES -gt 0 ] && echo "  - 볼륨: $REMAINING_VOLUMES개"
    [ $REMAINING_NETWORKS -gt 0 ] && echo "  - 네트워크: $REMAINING_NETWORKS개"
fi

# 5. dangling 이미지 정리 (선택사항)
DANGLING_IMAGES=$(docker images -f "dangling=true" -q)
if [ ! -z "$DANGLING_IMAGES" ]; then
    echo -e "${BLUE}[INFO]${NC} dangling 이미지 정리 중..."
    docker rmi $DANGLING_IMAGES 2>/dev/null || true
fi

echo -e "${GREEN}[DONE]${NC} 초기화 완료!"
