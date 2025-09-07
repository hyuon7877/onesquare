"""사진 업로드 관련 뷰"""
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
