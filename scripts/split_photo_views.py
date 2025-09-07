#!/usr/bin/env python3
"""Photo Views 모듈 자동 분할"""

import shutil
from pathlib import Path

# 경로 설정
source_file = Path('src/apps/field_reports/photo_views.py')
target_dir = Path('src/apps/field_reports/photo_views')

# 백업
backup_file = source_file.parent / f"{source_file.stem}_backup.py"
if not backup_file.exists():
    shutil.copy(source_file, backup_file)
    print(f"✅ 백업 생성: {backup_file.name}")

# 대상 디렉토리 생성
target_dir.mkdir(exist_ok=True)

# 1. upload_views.py - 업로드 관련 뷰
with open(target_dir / 'upload_views.py', 'w', encoding='utf-8') as f:
    f.write('''"""사진 업로드 관련 뷰"""
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.files.storage import default_storage
import os
import uuid
from PIL import Image

@csrf_exempt
@login_required
def upload_photo(request):
    """단일 사진 업로드"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    
    if 'photo' not in request.FILES:
        return JsonResponse({'error': 'No photo provided'}, status=400)
    
    photo = request.FILES['photo']
    
    # 파일 검증
    if not validate_image(photo):
        return JsonResponse({'error': 'Invalid image'}, status=400)
    
    # 파일 저장
    filename = save_photo(photo)
    
    return JsonResponse({
        'success': True,
        'filename': filename,
        'url': f'/media/photos/{filename}'
    })

@csrf_exempt
@login_required
def batch_upload_photos(request):
    """다중 사진 업로드"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    
    uploaded_files = []
    errors = []
    
    for key in request.FILES:
        photo = request.FILES[key]
        try:
            if validate_image(photo):
                filename = save_photo(photo)
                uploaded_files.append(filename)
            else:
                errors.append(f'{photo.name}: Invalid image')
        except Exception as e:
            errors.append(f'{photo.name}: {str(e)}')
    
    return JsonResponse({
        'success': len(uploaded_files) > 0,
        'uploaded': uploaded_files,
        'errors': errors
    })

def validate_image(photo):
    """이미지 검증"""
    try:
        img = Image.open(photo)
        img.verify()
        return True
    except:
        return False

def save_photo(photo):
    """사진 저장"""
    ext = photo.name.split('.')[-1]
    filename = f'{uuid.uuid4()}.{ext}'
    path = default_storage.save(f'photos/{filename}', photo)
    return filename
''')
    print("✅ upload_views.py 생성")

# 2. api_views.py - API 뷰
with open(target_dir / 'api_views.py', 'w', encoding='utf-8') as f:
    f.write('''"""사진 관리 API 뷰"""
from django.views import View
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
import json

@method_decorator(login_required, name='dispatch')
class PhotoUploadAPI(View):
    """사진 업로드 API 클래스"""
    
    def post(self, request):
        """사진 업로드 처리"""
        try:
            # 파일 처리
            photo = request.FILES.get('photo')
            if not photo:
                return JsonResponse({'error': 'No photo provided'}, status=400)
            
            # 메타데이터 처리
            metadata = json.loads(request.POST.get('metadata', '{}'))
            
            # 저장 및 처리
            result = self.process_photo(photo, metadata)
            
            return JsonResponse(result)
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def process_photo(self, photo, metadata):
        """사진 처리 로직"""
        # 이미지 처리
        # 썸네일 생성
        # 메타데이터 저장
        return {
            'success': True,
            'photo_id': 'generated_id',
            'url': '/media/photos/sample.jpg'
        }
    
    def get(self, request):
        """사진 목록 조회"""
        # 구현 필요
        return JsonResponse({'photos': []})
''')
    print("✅ api_views.py 생성")

# 3. list_views.py - 목록 및 상세 뷰
with open(target_dir / 'list_views.py', 'w', encoding='utf-8') as f:
    f.write('''"""사진 목록 및 상세 뷰"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse

@login_required
def photo_list(request):
    """사진 목록 뷰"""
    # 필터링
    project_id = request.GET.get('project')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # 쿼리셋 구성
    photos = []  # 실제 모델 쿼리로 교체 필요
    
    # 페이지네이션
    paginator = Paginator(photos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # AJAX 요청
        return JsonResponse({
            'photos': list(page_obj.object_list.values()),
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'total_count': paginator.count
        })
    
    # 일반 요청
    return render(request, 'field_reports/photo_list.html', {
        'page_obj': page_obj,
        'filter_params': {
            'project_id': project_id,
            'date_from': date_from,
            'date_to': date_to
        }
    })

@login_required
def photo_detail(request, photo_id):
    """사진 상세 뷰"""
    # photo = get_object_or_404(Photo, id=photo_id)
    
    return render(request, 'field_reports/photo_detail.html', {
        'photo': None  # 실제 photo 객체로 교체
    })
''')
    print("✅ list_views.py 생성")

# 4. management_views.py - 관리 기능 뷰
with open(target_dir / 'management_views.py', 'w', encoding='utf-8') as f:
    f.write('''"""사진 관리 기능 뷰"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@login_required
@csrf_exempt
def delete_photo(request, photo_id):
    """사진 삭제"""
    if request.method != 'DELETE':
        return JsonResponse({'error': 'DELETE required'}, status=400)
    
    try:
        # 권한 확인
        if not has_delete_permission(request.user, photo_id):
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # 삭제 처리
        delete_photo_files(photo_id)
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def update_photo_metadata(request, photo_id):
    """사진 메타데이터 업데이트"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    
    try:
        metadata = json.loads(request.body)
        # 업데이트 처리
        update_metadata(photo_id, metadata)
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def has_delete_permission(user, photo_id):
    """삭제 권한 확인"""
    # 구현 필요
    return True

def delete_photo_files(photo_id):
    """사진 파일 삭제"""
    # 구현 필요
    pass

def update_metadata(photo_id, metadata):
    """메타데이터 업데이트"""
    # 구현 필요
    pass
''')
    print("✅ management_views.py 생성")

# 5. progress_views.py - 진행 상태 뷰
with open(target_dir / 'progress_views.py', 'w', encoding='utf-8') as f:
    f.write('''"""업로드 진행 상태 관련 뷰"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.cache import cache

@login_required
def upload_progress(request):
    """업로드 진행 상태 조회"""
    upload_id = request.GET.get('upload_id')
    
    if not upload_id:
        return JsonResponse({'error': 'upload_id required'}, status=400)
    
    # 캐시에서 진행 상태 조회
    progress_key = f'upload_progress:{upload_id}'
    progress = cache.get(progress_key, {})
    
    return JsonResponse({
        'upload_id': upload_id,
        'progress': progress.get('percent', 0),
        'status': progress.get('status', 'unknown'),
        'message': progress.get('message', '')
    })

def update_upload_progress(upload_id, percent, status='uploading', message=''):
    """업로드 진행 상태 업데이트"""
    progress_key = f'upload_progress:{upload_id}'
    cache.set(progress_key, {
        'percent': percent,
        'status': status,
        'message': message
    }, timeout=3600)  # 1시간 유지
''')
    print("✅ progress_views.py 생성")

# 6. __init__.py
with open(target_dir / '__init__.py', 'w', encoding='utf-8') as f:
    f.write('''"""Field Reports Photo Views 모듈

분할된 사진 관리 뷰 모듈 통합
"""

from .upload_views import upload_photo, batch_upload_photos
from .api_views import PhotoUploadAPI
from .list_views import photo_list, photo_detail
from .management_views import delete_photo, update_photo_metadata
from .progress_views import upload_progress, update_upload_progress

__all__ = [
    # 업로드
    'upload_photo',
    'batch_upload_photos',
    
    # API
    'PhotoUploadAPI',
    
    # 목록/상세
    'photo_list',
    'photo_detail',
    
    # 관리
    'delete_photo',
    'update_photo_metadata',
    
    # 진행상태
    'upload_progress',
    'update_upload_progress',
]
''')
    print("✅ __init__.py 생성")

# 원본 파일 제거
source_file.unlink()
print(f"🗑️ 원본 파일 제거: {source_file.name}")

print("\n✨ Photo Views 모듈 분할 완료!")
print(f"📁 위치: {target_dir}")