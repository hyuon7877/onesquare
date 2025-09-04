#!/bin/bash

# WSL2 성능 최적화 스크립트
echo "WSL2 성능 최적화 시작..."

# .wslconfig 생성 (Windows 사용자 홈 디렉토리)
WIN_USER=$(cmd.exe /c "echo %USERNAME%" 2>/dev/null | tr -d '\r')
WIN_HOME="/mnt/c/Users/$WIN_USER"

if [ -d "$WIN_HOME" ]; then
    cat > "$WIN_HOME/.wslconfig" << 'CONFIG'
[wsl2]
memory=8GB
processors=4
swap=2GB
localhostForwarding=true

[experimental]
sparseVhd=true
CONFIG
    echo ".wslconfig 파일이 생성되었습니다: $WIN_HOME/.wslconfig"
    echo "WSL을 재시작하려면: wsl --shutdown"
fi

# Docker 데스크톱 없이 Docker 설치 확인
if ! command -v docker &> /dev/null; then
    echo "네이티브 Docker 설치를 권장합니다:"
    echo "curl -fsSL https://get.docker.com | sh"
    echo "sudo usermod -aG docker $USER"
fi

# 한글 환경 재확인
echo ""
echo "한글 환경 설정 확인:"
echo "LANG: $LANG"
echo "LC_ALL: $LC_ALL"

if [ -f ~/.vimrc ]; then
    echo "Vim 한글 설정: 완료"
else
    echo "Vim 한글 설정: 미완료"
fi

echo ""
echo "WSL2 최적화 팁:"
echo "1. Linux 파일시스템 사용 (/home/user/ 이하)"
echo "2. Windows 파일시스템 (/mnt/c/) 사용 피하기"
echo "3. Visual Studio Code에서 Remote-WSL 확장 사용"
echo "4. Windows Terminal에서 한글 지원 폰트 설정"
echo ""
echo "WSL2 최적화 완료!"
