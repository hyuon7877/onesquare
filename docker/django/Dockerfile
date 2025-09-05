# OneSquare Django 5 + PWA Container

ARG UBUNTU_VERSION=22.04
ARG PYTHON_VERSION=3.12

# Multi-stage build
FROM python:${PYTHON_VERSION}-slim-bookworm AS base

# Build arguments
ARG PROJECT_NAME=onesquare
ARG DEBIAN_FRONTEND=noninteractive

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    default-libmysqlclient-dev \
    libssl-dev \
    libffi-dev \
    libjpeg-dev \
    libpng-dev \
    libwebp-dev \
    libmagic1 \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create application user
RUN groupadd -r django && useradd -r -g django django

# Create application directory
RUN mkdir -p /var/www/html/${PROJECT_NAME}
WORKDIR /var/www/html/${PROJECT_NAME}

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# Copy project files
COPY src/ .

# Create necessary directories
RUN mkdir -p logs run media staticfiles && \
    chown -R django:django /var/www/html/${PROJECT_NAME}

# Copy and set permissions for entrypoint script
COPY docker/django/scripts/entrypoint.sh /scripts/entrypoint.sh
RUN chmod +x /scripts/entrypoint.sh

# Switch to django user
USER django

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Default command
CMD ["/scripts/entrypoint.sh"]