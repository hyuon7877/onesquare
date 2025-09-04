# Ubuntu 버전별 이미지 선택
ARG UBUNTU_VERSION=24.04
FROM ubuntu:${UBUNTU_VERSION} AS base

# 빌드 인자
ARG PYTHON_VERSION=3.12
ARG PROJECT_NAME

# 환경 변수 설정
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    TZ=Asia/Seoul \
    LANG=ko_KR.UTF-8 \
    LC_ALL=ko_KR.UTF-8 \
    LANGUAGE=ko_KR:ko:en_US:en

# 시스템 패키지 설치 및 Python 설치
RUN apt-get update && apt-get install -y \
    # 기본 도구
    software-properties-common \
    build-essential \
    pkg-config \
    curl \
    wget \
    vim \
    # Python 설치
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-dev \
    python${PYTHON_VERSION}-venv \
    python3-pip \
    # MySQL/MariaDB 클라이언트
    default-libmysqlclient-dev \
    mariadb-client \
    # 네트워크 도구
    netcat-openbsd \
    # 로케일
    locales \
    # 폰트 (한글 지원)
    fonts-nanum \
    fontconfig \
    # 문서 처리
    wkhtmltopdf \
    # 시간대
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Python 기본 버전 설정
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python${PYTHON_VERSION} 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python${PYTHON_VERSION} 1

# 한글 로케일 생성 및 설정
RUN sed -i '/ko_KR.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen ko_KR.UTF-8 && \
    update-locale LANG=ko_KR.UTF-8 LC_ALL=ko_KR.UTF-8

# 타임존 설정
RUN ln -snf /usr/share/zoneinfo/Asia/Seoul /etc/localtime && \
    echo "Asia/Seoul" > /etc/timezone && \
    dpkg-reconfigure -f noninteractive tzdata

# 작업 디렉토리 설정
WORKDIR /var/www/html/${PROJECT_NAME}

# 가상환경 생성 및 활성화
RUN python${PYTHON_VERSION} -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# pip 업그레이드 및 필수 패키지 설치
COPY requirements.txt /tmp/
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/requirements.txt

# 폰트 캐시 갱신
RUN fc-cache -fv

# 사용자 생성 (선택적)
RUN useradd -ms /bin/bash django

EXPOSE 8000
