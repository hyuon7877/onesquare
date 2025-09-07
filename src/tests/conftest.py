"""Pytest 설정 파일

테스트 픽스처와 공통 설정
"""

import pytest
import os
import sys
from pathlib import Path

# Django 설정
sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client

User = get_user_model()


@pytest.fixture
def client():
    """테스트 클라이언트"""
    return Client()


@pytest.fixture
def user():
    """일반 사용자"""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def admin_user():
    """관리자 사용자"""
    return User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass123'
    )


@pytest.fixture
def authenticated_client(client, user):
    """인증된 클라이언트"""
    client.login(username='testuser', password='testpass123')
    return client


@pytest.fixture
def admin_client(client, admin_user):
    """관리자 클라이언트"""
    client.login(username='admin', password='adminpass123')
    return client


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """모든 테스트에서 DB 접근 허용"""
    pass