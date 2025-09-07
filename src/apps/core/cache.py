"""캐싱 전략 모듈

Django 캐시 프레임워크를 활용한 최적화된 캐싱 전략
"""

from django.core.cache import cache
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.conf import settings
from functools import wraps
import hashlib
import json
import logging

logger = logging.getLogger(__name__)

# 캐시 타임아웃 설정
CACHE_TTL = getattr(settings, 'CACHE_TTL', DEFAULT_TIMEOUT)
SHORT_CACHE_TTL = 60 * 5  # 5분
MEDIUM_CACHE_TTL = 60 * 30  # 30분
LONG_CACHE_TTL = 60 * 60 * 24  # 24시간


class CacheManager:
    """캐시 관리 클래스"""
    
    def __init__(self, prefix='app'):
        self.prefix = prefix
        
    def make_key(self, key_parts):
        """캐시 키 생성"""
        if isinstance(key_parts, (list, tuple)):
            key = ':'.join(str(part) for part in key_parts)
        else:
            key = str(key_parts)
        return f'{self.prefix}:{key}'
    
    def get(self, key):
        """캐시에서 값 가져오기"""
        cache_key = self.make_key(key)
        value = cache.get(cache_key)
        if value:
            logger.debug(f'Cache hit: {cache_key}')
        else:
            logger.debug(f'Cache miss: {cache_key}')
        return value
    
    def set(self, key, value, timeout=None):
        """캐시에 값 저장"""
        cache_key = self.make_key(key)
        timeout = timeout or CACHE_TTL
        cache.set(cache_key, value, timeout)
        logger.debug(f'Cache set: {cache_key} (timeout: {timeout}s)')
        return value
    
    def delete(self, key):
        """캐시에서 값 삭제"""
        cache_key = self.make_key(key)
        cache.delete(cache_key)
        logger.debug(f'Cache delete: {cache_key}')
    
    def clear_pattern(self, pattern):
        """패턴과 일치하는 캐시 키 모두 삭제"""
        full_pattern = f'{self.prefix}:{pattern}*'
        cache.delete_pattern(full_pattern)
        logger.debug(f'Cache clear pattern: {full_pattern}')
    
    def get_or_set(self, key, callable_or_value, timeout=None):
        """캐시에서 가져오거나 없으면 설정"""
        cache_key = self.make_key(key)
        value = cache.get(cache_key)
        
        if value is None:
            if callable(callable_or_value):
                value = callable_or_value()
            else:
                value = callable_or_value
            
            timeout = timeout or CACHE_TTL
            cache.set(cache_key, value, timeout)
            logger.debug(f'Cache get_or_set - set: {cache_key}')
        else:
            logger.debug(f'Cache get_or_set - hit: {cache_key}')
        
        return value


def cache_key_from_args(*args, **kwargs):
    """함수 인자로부터 캐시 키 생성"""
    key_data = {
        'args': args,
        'kwargs': kwargs
    }
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()


def cached(timeout=None, key_prefix=None):
    """함수 결과 캐싱 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            cache_key_parts = [
                key_prefix or func.__module__,
                func.__name__,
                cache_key_from_args(*args, **kwargs)
            ]
            cache_key = ':'.join(cache_key_parts)
            
            # 캐시에서 확인
            result = cache.get(cache_key)
            if result is not None:
                logger.debug(f'Cached function hit: {func.__name__}')
                return result
            
            # 함수 실행 및 캐싱
            result = func(*args, **kwargs)
            cache_timeout = timeout or CACHE_TTL
            cache.set(cache_key, result, cache_timeout)
            logger.debug(f'Cached function miss: {func.__name__} (cached for {cache_timeout}s)')
            
            return result
        
        wrapper.invalidate = lambda *args, **kwargs: cache.delete(
            ':'.join([
                key_prefix or func.__module__,
                func.__name__,
                cache_key_from_args(*args, **kwargs)
            ])
        )
        
        return wrapper
    return decorator


def cache_page_content(timeout=None):
    """뷰 응답 캐싱 데코레이터"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # 인증된 사용자는 캐싱하지 않음
            if request.user.is_authenticated:
                return view_func(request, *args, **kwargs)
            
            # 캐시 키 생성 (URL 기반)
            cache_key = f'page:{request.path}:{request.GET.urlencode()}'
            
            # 캐시 확인
            cached_response = cache.get(cache_key)
            if cached_response:
                logger.debug(f'Page cache hit: {request.path}')
                return cached_response
            
            # 뷰 실행 및 캐싱
            response = view_func(request, *args, **kwargs)
            if response.status_code == 200:
                cache_timeout = timeout or MEDIUM_CACHE_TTL
                cache.set(cache_key, response, cache_timeout)
                logger.debug(f'Page cache miss: {request.path} (cached for {cache_timeout}s)')
            
            return response
        return wrapper
    return decorator


class QueryCacheManager:
    """데이터베이스 쿼리 캐싱 관리"""
    
    @staticmethod
    @cached(timeout=SHORT_CACHE_TTL, key_prefix='query')
    def get_model_count(model_class):
        """모델 전체 개수 캐싱"""
        return model_class.objects.count()
    
    @staticmethod
    @cached(timeout=MEDIUM_CACHE_TTL, key_prefix='query')
    def get_model_list(model_class, limit=100):
        """모델 리스트 캐싱"""
        return list(model_class.objects.all()[:limit])
    
    @staticmethod
    def invalidate_model_cache(model_class):
        """모델 관련 캐시 무효화"""
        prefix = f'query:{model_class.__module__}.{model_class.__name__}'
        cache.delete_pattern(f'{prefix}:*')
        logger.info(f'Invalidated cache for model: {model_class.__name__}')


class SessionCacheManager:
    """세션 기반 캐싱"""
    
    @staticmethod
    def get_user_cache(user, key):
        """사용자별 캐시 가져오기"""
        cache_key = f'user:{user.id}:{key}'
        return cache.get(cache_key)
    
    @staticmethod
    def set_user_cache(user, key, value, timeout=None):
        """사용자별 캐시 설정"""
        cache_key = f'user:{user.id}:{key}'
        timeout = timeout or MEDIUM_CACHE_TTL
        cache.set(cache_key, value, timeout)
        return value
    
    @staticmethod
    def clear_user_cache(user):
        """사용자의 모든 캐시 삭제"""
        pattern = f'user:{user.id}:*'
        cache.delete_pattern(pattern)
        logger.info(f'Cleared all cache for user: {user.id}')


class NotionCacheManager:
    """Notion API 응답 캐싱"""
    
    @staticmethod
    @cached(timeout=SHORT_CACHE_TTL, key_prefix='notion')
    def get_database_content(database_id):
        """Notion 데이터베이스 캐싱"""
        # 실제 Notion API 호출은 별도 서비스에서
        pass
    
    @staticmethod
    @cached(timeout=LONG_CACHE_TTL, key_prefix='notion')
    def get_page_content(page_id):
        """Notion 페이지 캐싱"""
        # 실제 Notion API 호출은 별도 서비스에서
        pass
    
    @staticmethod
    def invalidate_notion_cache():
        """모든 Notion 캐시 무효화"""
        cache.delete_pattern('notion:*')
        logger.info('Invalidated all Notion cache')


# 싱글톤 인스턴스
default_cache_manager = CacheManager()
query_cache = QueryCacheManager()
session_cache = SessionCacheManager()
notion_cache = NotionCacheManager()


def clear_all_cache():
    """모든 캐시 삭제"""
    cache.clear()
    logger.warning('All cache cleared!')


def get_cache_stats():
    """캐시 통계 정보"""
    # Django 캐시 백엔드에 따라 구현 다름
    try:
        if hasattr(cache, '_cache'):
            # Locmem 백엔드
            return {
                'keys': len(cache._cache),
                'backend': 'locmem'
            }
        elif hasattr(cache, '_client'):
            # Redis/Memcached 백엔드
            info = cache._client.info()
            return {
                'keys': info.get('db0', {}).get('keys', 0),
                'backend': 'redis/memcached',
                'memory': info.get('used_memory_human', 'N/A')
            }
    except:
        pass
    
    return {'status': 'Cache stats not available'}