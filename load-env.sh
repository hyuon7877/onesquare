#!/bin/bash
# .env 파일의 환경변수를 현재 셸에 로드
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "환경변수가 로드되었습니다."
    echo "PROJECT_NAME: $PROJECT_NAME"
else
    echo ".env 파일을 찾을 수 없습니다."
fi
