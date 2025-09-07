#!/bin/bash

# OneSquare 아키텍처 다이어그램 뷰어
echo "🏗️ OneSquare 아키텍처 다이어그램 뷰어"
echo "=================================="
echo ""
echo "다이어그램을 보는 방법을 선택하세요:"
echo ""
echo "1. 브라우저에서 보기 (HTML)"
echo "2. Mermaid Live Editor에서 보기"
echo "3. Markdown 파일 직접 보기"
echo ""
read -p "선택 (1-3): " choice

case $choice in
    1)
        echo "브라우저에서 다이어그램을 엽니다..."
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            xdg-open docs/view-architecture.html
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            open docs/view-architecture.html
        elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
            start docs/view-architecture.html
        else
            echo "파일 경로: docs/view-architecture.html"
        fi
        ;;
    2)
        echo "Mermaid Live Editor 열기..."
        echo "https://mermaid.live 에서 docs/architecture.md의 코드를 붙여넣으세요"
        ;;
    3)
        echo "Markdown 파일 내용:"
        echo ""
        cat docs/architecture.md | grep -A 20 "```mermaid"
        ;;
    *)
        echo "잘못된 선택입니다."
        ;;
esac