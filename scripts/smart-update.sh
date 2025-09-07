#!/bin/bash
# OneSquare 스마트 업데이트 스크립트
# 변경사항이 있을 때만 다이어그램 업데이트

set -e

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🔍 OneSquare 모듈 변경 감지 중...${NC}"

# MODULE_TRACKER.md의 해시값 저장
HASH_FILE=".taskmaster/.module_hash"
CURRENT_HASH=$(md5sum MODULE_TRACKER.md | cut -d' ' -f1)

# 이전 해시값 확인
if [ -f "$HASH_FILE" ]; then
    PREV_HASH=$(cat "$HASH_FILE")
else
    PREV_HASH=""
fi

# 변경사항 확인
if [ "$CURRENT_HASH" != "$PREV_HASH" ]; then
    echo -e "${YELLOW}📝 MODULE_TRACKER.md 변경 감지!${NC}"
    
    # 다이어그램 업데이트
    echo -e "${GREEN}🔄 아키텍처 다이어그램 업데이트 중...${NC}"
    python3 scripts/update-architecture.py
    
    # 새 해시값 저장
    echo "$CURRENT_HASH" > "$HASH_FILE"
    
    echo -e "${GREEN}✅ 다이어그램 업데이트 완료!${NC}"
    echo -e "${CYAN}📊 보기: docs/architecture.md${NC}"
    
    # 변경사항 요약
    echo -e "\n${YELLOW}변경사항:${NC}"
    git diff --stat MODULE_TRACKER.md 2>/dev/null || echo "Git 외부에서 실행됨"
else
    echo -e "${GREEN}✨ 변경사항 없음 - 다이어그램이 최신 상태입니다${NC}"
fi

# 옵션: 브라우저에서 바로 열기
read -p "브라우저에서 다이어그램을 보시겠습니까? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        xdg-open docs/view-architecture.html
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        start docs/view-architecture.html
    else
        echo "docs/view-architecture.html 파일을 브라우저에서 직접 열어주세요"
    fi
fi