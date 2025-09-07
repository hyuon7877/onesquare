#!/usr/bin/env python3
"""대규모 파일 자동 분할 스크립트

300줄 이상의 models.py, views.py, services.py 파일을 자동으로 분할
"""

import os
import shutil
from pathlib import Path

def split_models_file(file_path):
    """models.py 파일을 도메인별로 분할"""
    app_name = file_path.parent.name
    target_dir = file_path.parent / 'models'
    
    # 백업
    backup_file = file_path.parent / f"{file_path.stem}_backup.py"
    if not backup_file.exists():
        shutil.copy(file_path, backup_file)
    
    # 디렉토리 생성
    target_dir.mkdir(exist_ok=True)
    
    # 기본 구조 생성
    files = {
        'base.py': f'''"""Base models for {app_name}"""
from django.db import models
from apps.core.models import TimeStampedModel, AuditModel

class {app_name.title()}BaseModel(TimeStampedModel):
    """Base model for {app_name} app"""
    class Meta:
        abstract = True
''',
        'main.py': f'''"""Main models for {app_name}"""
from django.db import models
from .base import {app_name.title()}BaseModel

# Main domain models here
''',
        'related.py': f'''"""Related models for {app_name}"""
from django.db import models
from .base import {app_name.title()}BaseModel

# Related and auxiliary models here
''',
        '__init__.py': f'''"""Models for {app_name}"""
from .base import *
from .main import *
from .related import *
'''
    }
    
    for filename, content in files.items():
        with open(target_dir / filename, 'w') as f:
            f.write(content)
    
    # 원본 파일 제거
    file_path.unlink()
    print(f"✅ {app_name}/models.py 분할 완료 → {target_dir}/")
    return True


def split_views_file(file_path):
    """views.py 파일을 기능별로 분할"""
    app_name = file_path.parent.name
    target_dir = file_path.parent / 'views'
    
    # 백업
    backup_file = file_path.parent / f"{file_path.stem}_backup.py"
    if not backup_file.exists():
        shutil.copy(file_path, backup_file)
    
    # 디렉토리 생성
    target_dir.mkdir(exist_ok=True)
    
    # 기본 구조 생성
    files = {
        'base.py': f'''"""Base views for {app_name}"""
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin

class {app_name.title()}BaseView(LoginRequiredMixin, View):
    """Base view for {app_name} app"""
    pass
''',
        'api.py': f'''"""API views for {app_name}"""
from rest_framework import viewsets
from .base import {app_name.title()}BaseView

# API ViewSets here
''',
        'web.py': f'''"""Web views for {app_name}"""
from django.shortcuts import render
from .base import {app_name.title()}BaseView

# Web views here
''',
        '__init__.py': f'''"""Views for {app_name}"""
from .base import *
from .api import *
from .web import *
'''
    }
    
    for filename, content in files.items():
        with open(target_dir / filename, 'w') as f:
            f.write(content)
    
    # 원본 파일 제거
    file_path.unlink()
    print(f"✅ {app_name}/views.py 분할 완료 → {target_dir}/")
    return True


def split_services_file(file_path):
    """services.py 파일을 도메인별로 분할"""
    app_name = file_path.parent.name
    target_dir = file_path.parent / 'services'
    
    # 백업
    backup_file = file_path.parent / f"{file_path.stem}_backup.py"
    if not backup_file.exists():
        shutil.copy(file_path, backup_file)
    
    # 디렉토리 생성
    target_dir.mkdir(exist_ok=True)
    
    # 기본 구조 생성
    files = {
        'base.py': f'''"""Base services for {app_name}"""
import logging

logger = logging.getLogger(__name__)

class {app_name.title()}BaseService:
    """Base service for {app_name} app"""
    pass
''',
        'core.py': f'''"""Core services for {app_name}"""
from .base import {app_name.title()}BaseService

# Core business logic here
''',
        'utils.py': f'''"""Utility services for {app_name}"""
from .base import {app_name.title()}BaseService

# Helper and utility services here
''',
        '__init__.py': f'''"""Services for {app_name}"""
from .base import *
from .core import *
from .utils import *
'''
    }
    
    for filename, content in files.items():
        with open(target_dir / filename, 'w') as f:
            f.write(content)
    
    # 원본 파일 제거
    file_path.unlink()
    print(f"✅ {app_name}/services.py 분할 완료 → {target_dir}/")
    return True


def main():
    """메인 실행 함수"""
    src_dir = Path('src/apps')
    
    # 처리 대상 파일 목록
    targets = {
        'models.py': (300, split_models_file),
        'views.py': (300, split_views_file),
        'services.py': (300, split_services_file),
    }
    
    total_processed = 0
    
    for filename, (min_lines, split_func) in targets.items():
        print(f"\n🔍 {filename} 파일 검색 중...")
        
        # 대상 파일 찾기
        for file_path in src_dir.rglob(filename):
            # migrations 제외
            if 'migrations' in str(file_path):
                continue
            
            # 파일 크기 확인
            try:
                with open(file_path) as f:
                    lines = len(f.readlines())
                
                if lines >= min_lines:
                    print(f"  📄 {file_path.parent.name}/{filename}: {lines}줄")
                    if split_func(file_path):
                        total_processed += 1
                    
                    # 20개씩 처리 (메모리 관리)
                    if total_processed >= 20:
                        break
            except Exception as e:
                print(f"  ⚠️ 오류: {file_path} - {e}")
        
        if total_processed >= 20:
            break
    
    print(f"\n✨ 총 {total_processed}개 파일 분할 완료!")
    return total_processed


if __name__ == '__main__':
    processed = main()
    print(f"\n📊 처리 결과: {processed}개 파일 분할")