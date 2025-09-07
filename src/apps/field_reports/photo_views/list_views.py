"""사진 목록 및 상세 뷰"""
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
