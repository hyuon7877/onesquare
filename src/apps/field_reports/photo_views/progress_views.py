"""업로드 진행 상태 관련 뷰"""
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
