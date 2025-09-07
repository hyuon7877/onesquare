from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, Count, F
from django.core.paginator import Paginator
from django.utils import timezone
from .models import SearchHistory, SearchIndex, SavedSearch, TrendingSearch, SearchSuggestion
from field_reports.models import FieldReport
from collaboration.models import Comment, Activity
from django.contrib.auth.models import User
import json


@login_required
def unified_search(request):
    """통합 검색 API"""
    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'all')
    page = request.GET.get('page', 1)
    
    if not query:
        return JsonResponse({'results': [], 'message': '검색어를 입력하세요.'})
    
    # 검색 기록 저장
    if query:
        SearchHistory.objects.create(
            user=request.user,
            query=query,
            search_type=search_type,
            results_count=0  # 나중에 업데이트
        )
        
        # 인기 검색어 업데이트
        TrendingSearch.update_trending(query)
    
    results = []
    
    # 검색 인덱스에서 검색
    search_results = SearchIndex.objects.filter(
        Q(title__icontains=query) |
        Q(content__icontains=query) |
        Q(tags__contains=query)
    )
    
    # 검색 타입별 필터링
    if search_type == 'reports':
        search_results = search_results.filter(category='report')
    elif search_type == 'comments':
        search_results = search_results.filter(category='comment')
    elif search_type == 'users':
        search_results = search_results.filter(category='user')
    elif search_type == 'activities':
        search_results = search_results.filter(category='activity')
    
    # 가중치와 최신순으로 정렬
    search_results = search_results.order_by('-search_weight', '-created_at')
    
    # 페이지네이션
    paginator = Paginator(search_results, 20)
    page_obj = paginator.get_page(page)
    
    # 결과 포맷팅
    for result in page_obj:
        result_data = {
            'id': result.id,
            'type': result.category,
            'title': result.title,
            'content': result.content[:200] + '...' if len(result.content) > 200 else result.content,
            'tags': result.tags,
            'author': {
                'id': result.author.id,
                'username': result.author.username,
                'full_name': result.author.get_full_name() or result.author.username
            } if result.author else None,
            'created_at': result.created_at.isoformat(),
            'url': f'/{result.category}/{result.object_id}/'  # 동적 URL 생성
        }
        results.append(result_data)
    
    # 검색 기록 업데이트
    SearchHistory.objects.filter(
        user=request.user,
        query=query
    ).order_by('-created_at').first().update(
        results_count=paginator.count
    )
    
    return JsonResponse({
        'results': results,
        'total_count': paginator.count,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'total_pages': paginator.num_pages,
        'current_page': page_obj.number,
        'query': query,
        'search_type': search_type
    })


@login_required
def autocomplete(request):
    """자동완성 제안 API"""
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category')
    
    if not query or len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    # 검색 제안 가져오기
    suggestions = SearchSuggestion.get_suggestions(query, category, limit=10)
    
    suggestions_data = []
    for suggestion in suggestions:
        suggestions_data.append({
            'keyword': suggestion.keyword,
            'suggestion': suggestion.suggestion,
            'category': suggestion.category,
            'weight': suggestion.weight
        })
    
    # 인기 검색어 추가
    trending = TrendingSearch.objects.filter(
        keyword__istartswith=query.lower()
    )[:5]
    
    for trend in trending:
        suggestions_data.append({
            'keyword': trend.keyword,
            'suggestion': trend.keyword,
            'category': 'trending',
            'weight': trend.count
        })
    
    # 중복 제거 및 정렬
    seen = set()
    unique_suggestions = []
    for item in suggestions_data:
        if item['suggestion'] not in seen:
            seen.add(item['suggestion'])
            unique_suggestions.append(item)
    
    return JsonResponse({'suggestions': unique_suggestions[:10]})


@login_required
def search_history(request):
    """검색 기록 조회"""
    history = SearchHistory.objects.filter(
        user=request.user
    ).order_by('-created_at')[:20]
    
    history_data = []
    for item in history:
        history_data.append({
            'id': item.id,
            'query': item.query,
            'search_type': item.search_type,
            'search_type_display': item.get_search_type_display(),
            'results_count': item.results_count,
            'created_at': item.created_at.isoformat()
        })
    
    return JsonResponse({'history': history_data})


@login_required
@require_http_methods(["DELETE"])
def clear_search_history(request):
    """검색 기록 삭제"""
    SearchHistory.objects.filter(user=request.user).delete()
    return JsonResponse({'success': True, 'message': '검색 기록이 삭제되었습니다.'})


@login_required
def trending_searches(request):
    """인기 검색어 조회"""
    period = request.GET.get('period', 'all')  # all, daily, weekly, monthly
    limit = int(request.GET.get('limit', 10))
    
    trending = TrendingSearch.objects.all()
    
    # 기간별 필터링
    if period == 'daily':
        trending = trending.order_by('-daily_count')
    elif period == 'weekly':
        trending = trending.order_by('-weekly_count')
    elif period == 'monthly':
        trending = trending.order_by('-monthly_count')
    else:
        trending = trending.order_by('-count')
    
    trending = trending[:limit]
    
    trending_data = []
    for item in trending:
        trending_data.append({
            'keyword': item.keyword,
            'count': item.count,
            'daily_count': item.daily_count,
            'weekly_count': item.weekly_count,
            'monthly_count': item.monthly_count,
            'last_searched': item.last_searched.isoformat()
        })
    
    return JsonResponse({'trending': trending_data})


@login_required
def saved_searches(request):
    """저장된 검색 필터 목록"""
    searches = SavedSearch.objects.filter(
        Q(user=request.user) | Q(is_shared=True)
    ).order_by('-is_default', 'name')
    
    searches_data = []
    for search in searches:
        searches_data.append({
            'id': search.id,
            'name': search.name,
            'description': search.description,
            'query': search.query,
            'filters': search.filters,
            'is_default': search.is_default,
            'is_shared': search.is_shared,
            'is_mine': search.user == request.user,
            'created_at': search.created_at.isoformat()
        })
    
    return JsonResponse({'saved_searches': searches_data})


@login_required
@require_http_methods(["POST"])
def save_search(request):
    """검색 필터 저장"""
    data = json.loads(request.body)
    
    name = data.get('name', '').strip()
    if not name:
        return JsonResponse({'error': '필터 이름을 입력하세요.'}, status=400)
    
    # 중복 확인
    if SavedSearch.objects.filter(user=request.user, name=name).exists():
        return JsonResponse({'error': '이미 존재하는 필터 이름입니다.'}, status=400)
    
    saved_search = SavedSearch.objects.create(
        user=request.user,
        name=name,
        description=data.get('description', ''),
        query=data.get('query', ''),
        filters=data.get('filters', {}),
        is_default=data.get('is_default', False),
        is_shared=data.get('is_shared', False)
    )
    
    # 기본 필터로 설정 시 다른 필터의 기본 설정 해제
    if saved_search.is_default:
        SavedSearch.objects.filter(
            user=request.user
        ).exclude(id=saved_search.id).update(is_default=False)
    
    return JsonResponse({
        'success': True,
        'message': '검색 필터가 저장되었습니다.',
        'saved_search': {
            'id': saved_search.id,
            'name': saved_search.name
        }
    })


@login_required
@require_http_methods(["PUT", "DELETE"])
def manage_saved_search(request, search_id):
    """저장된 검색 필터 수정/삭제"""
    saved_search = get_object_or_404(SavedSearch, id=search_id, user=request.user)
    
    if request.method == 'PUT':
        data = json.loads(request.body)
        
        saved_search.name = data.get('name', saved_search.name)
        saved_search.description = data.get('description', saved_search.description)
        saved_search.query = data.get('query', saved_search.query)
        saved_search.filters = data.get('filters', saved_search.filters)
        saved_search.is_default = data.get('is_default', saved_search.is_default)
        saved_search.is_shared = data.get('is_shared', saved_search.is_shared)
        saved_search.save()
        
        # 기본 필터로 설정 시 다른 필터의 기본 설정 해제
        if saved_search.is_default:
            SavedSearch.objects.filter(
                user=request.user
            ).exclude(id=saved_search.id).update(is_default=False)
        
        return JsonResponse({'success': True, 'message': '검색 필터가 수정되었습니다.'})
    
    else:  # DELETE
        saved_search.delete()
        return JsonResponse({'success': True, 'message': '검색 필터가 삭제되었습니다.'})


@login_required
@require_http_methods(["POST"])
def apply_saved_search(request, search_id):
    """저장된 검색 필터 적용"""
    saved_search = get_object_or_404(
        SavedSearch,
        Q(id=search_id) & (Q(user=request.user) | Q(is_shared=True))
    )
    
    # 검색 인덱스에 필터 적용
    queryset = SearchIndex.objects.all()
    queryset = saved_search.apply_filters(queryset)
    
    # 페이지네이션
    page = request.GET.get('page', 1)
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(page)
    
    # 결과 포맷팅
    results = []
    for result in page_obj:
        result_data = {
            'id': result.id,
            'type': result.category,
            'title': result.title,
            'content': result.content[:200] + '...' if len(result.content) > 200 else result.content,
            'tags': result.tags,
            'author': {
                'id': result.author.id,
                'username': result.author.username,
                'full_name': result.author.get_full_name() or result.author.username
            } if result.author else None,
            'created_at': result.created_at.isoformat(),
            'url': f'/{result.category}/{result.object_id}/'
        }
        results.append(result_data)
    
    return JsonResponse({
        'results': results,
        'total_count': paginator.count,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'total_pages': paginator.num_pages,
        'current_page': page_obj.number,
        'filter_name': saved_search.name
    })


@login_required
@require_http_methods(["POST"])
def index_content(request):
    """콘텐츠를 검색 인덱스에 추가 (관리자용)"""
    if not request.user.is_staff:
        return JsonResponse({'error': '권한이 없습니다.'}, status=403)
    
    data = json.loads(request.body)
    
    content_type_id = data.get('content_type_id')
    object_id = data.get('object_id')
    
    if not content_type_id or not object_id:
        return JsonResponse({'error': '필수 파라미터가 누락되었습니다.'}, status=400)
    
    content_type = get_object_or_404(ContentType, id=content_type_id)
    
    # 해당 객체 가져오기
    model_class = content_type.model_class()
    try:
        obj = model_class.objects.get(id=object_id)
    except model_class.DoesNotExist:
        return JsonResponse({'error': '객체를 찾을 수 없습니다.'}, status=404)
    
    # 인덱스 생성 또는 업데이트
    index, created = SearchIndex.objects.update_or_create(
        content_type=content_type,
        object_id=object_id,
        defaults={
            'title': getattr(obj, 'title', str(obj)),
            'content': getattr(obj, 'content', ''),
            'tags': getattr(obj, 'tags', []),
            'author': getattr(obj, 'author', None) or getattr(obj, 'user', None),
            'category': content_type.model,
            'search_weight': data.get('weight', 1.0)
        }
    )
    
    # 검색 벡터 업데이트
    index.update_search_vector()
    
    return JsonResponse({
        'success': True,
        'message': '검색 인덱스가 업데이트되었습니다.',
        'created': created
    })


@login_required
def advanced_filter(request):
    """고급 필터링 API"""
    filters = {}
    
    # 날짜 범위 필터
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        filters['created_at__gte'] = date_from
    if date_to:
        filters['created_at__lte'] = date_to
    
    # 작성자 필터
    author_id = request.GET.get('author_id')
    if author_id:
        filters['author_id'] = author_id
    
    # 카테고리 필터
    category = request.GET.get('category')
    if category:
        filters['category'] = category
    
    # 상태 필터
    status = request.GET.get('status')
    if status:
        filters['status'] = status
    
    # 태그 필터
    tags = request.GET.getlist('tags')
    if tags:
        filters['tags__contains'] = tags
    
    # 필터 적용
    results = SearchIndex.objects.filter(**filters)
    
    # 정렬
    sort_by = request.GET.get('sort', '-created_at')
    results = results.order_by(sort_by)
    
    # 페이지네이션
    page = request.GET.get('page', 1)
    paginator = Paginator(results, 20)
    page_obj = paginator.get_page(page)
    
    # 결과 포맷팅
    results_data = []
    for result in page_obj:
        result_data = {
            'id': result.id,
            'type': result.category,
            'title': result.title,
            'content': result.content[:200] + '...' if len(result.content) > 200 else result.content,
            'tags': result.tags,
            'author': {
                'id': result.author.id,
                'username': result.author.username,
                'full_name': result.author.get_full_name() or result.author.username
            } if result.author else None,
            'created_at': result.created_at.isoformat(),
            'status': result.status,
            'url': f'/{result.category}/{result.object_id}/'
        }
        results_data.append(result_data)
    
    return JsonResponse({
        'results': results_data,
        'total_count': paginator.count,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
        'total_pages': paginator.num_pages,
        'current_page': page_obj.number,
        'applied_filters': filters
    })