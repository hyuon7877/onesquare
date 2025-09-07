from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib.postgres.indexes import GinIndex


class SearchHistory(models.Model):
    """검색 기록 모델"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='search_history')
    query = models.CharField(max_length=255, verbose_name='검색어')
    results_count = models.IntegerField(default=0, verbose_name='결과 수')
    search_type = models.CharField(
        max_length=50,
        choices=[
            ('all', '전체'),
            ('reports', '리포트'),
            ('comments', '댓글'),
            ('users', '사용자'),
            ('activities', '활동'),
        ],
        default='all'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['query']),
        ]
        verbose_name = '검색 기록'
        verbose_name_plural = '검색 기록'
    
    def __str__(self):
        return f"{self.user.username}: {self.query}"


class SearchIndex(models.Model):
    """통합 검색 인덱스 모델"""
    
    # 인덱싱할 콘텐츠
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # 검색 필드
    title = models.CharField(max_length=500, blank=True)
    content = models.TextField()
    tags = models.JSONField(default=list, blank=True)
    
    # 메타데이터
    author = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    category = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=50, blank=True)
    
    # 검색 가중치
    search_weight = models.FloatField(default=1.0)
    
    # 시간 정보
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # 전문 검색을 위한 벡터 필드 (PostgreSQL 사용 시)
    search_vector = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-search_weight', '-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['author', 'category']),
            models.Index(fields=['created_at']),
        ]
        verbose_name = '검색 인덱스'
        verbose_name_plural = '검색 인덱스'
    
    def __str__(self):
        return f"{self.title or self.content[:50]}"
    
    def update_search_vector(self):
        """검색 벡터 업데이트"""
        self.search_vector = f"{self.title} {self.content} {' '.join(self.tags)}"
        self.save()


class SavedSearch(models.Model):
    """저장된 검색 필터"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_searches')
    name = models.CharField(max_length=100, verbose_name='필터 이름')
    description = models.TextField(blank=True, verbose_name='설명')
    
    # 검색 조건
    query = models.CharField(max_length=255, blank=True, verbose_name='검색어')
    filters = models.JSONField(default=dict, verbose_name='필터 조건')
    
    # 설정
    is_default = models.BooleanField(default=False, verbose_name='기본 필터')
    is_shared = models.BooleanField(default=False, verbose_name='공유')
    
    # 시간 정보
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default', 'name']
        unique_together = [['user', 'name']]
        verbose_name = '저장된 검색'
        verbose_name_plural = '저장된 검색'
    
    def __str__(self):
        return f"{self.user.username}: {self.name}"
    
    def apply_filters(self, queryset):
        """필터 적용"""
        if self.query:
            queryset = queryset.filter(
                models.Q(title__icontains=self.query) |
                models.Q(content__icontains=self.query)
            )
        
        for field, value in self.filters.items():
            if value:
                queryset = queryset.filter(**{field: value})
        
        return queryset


class TrendingSearch(models.Model):
    """인기 검색어"""
    keyword = models.CharField(max_length=100, unique=True, verbose_name='검색어')
    count = models.IntegerField(default=1, verbose_name='검색 횟수')
    last_searched = models.DateTimeField(auto_now=True, verbose_name='마지막 검색')
    
    # 기간별 통계
    daily_count = models.IntegerField(default=0)
    weekly_count = models.IntegerField(default=0)
    monthly_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-count', '-last_searched']
        verbose_name = '인기 검색어'
        verbose_name_plural = '인기 검색어'
    
    def __str__(self):
        return f"{self.keyword} ({self.count})"
    
    @classmethod
    def update_trending(cls, keyword):
        """검색어 카운트 업데이트"""
        trending, created = cls.objects.get_or_create(
            keyword=keyword.lower()
        )
        trending.count += 1
        trending.daily_count += 1
        trending.weekly_count += 1
        trending.monthly_count += 1
        trending.save()
        return trending


class SearchSuggestion(models.Model):
    """검색 자동완성 제안"""
    keyword = models.CharField(max_length=100, unique=True, verbose_name='키워드')
    suggestion = models.CharField(max_length=255, verbose_name='제안어')
    weight = models.FloatField(default=1.0, verbose_name='가중치')
    usage_count = models.IntegerField(default=0, verbose_name='사용 횟수')
    
    # 카테고리별 제안
    category = models.CharField(
        max_length=50,
        choices=[
            ('general', '일반'),
            ('report', '리포트'),
            ('user', '사용자'),
            ('location', '위치'),
            ('tag', '태그'),
        ],
        default='general'
    )
    
    class Meta:
        ordering = ['-weight', '-usage_count']
        indexes = [
            models.Index(fields=['keyword', 'category']),
        ]
        verbose_name = '검색 제안'
        verbose_name_plural = '검색 제안'
    
    def __str__(self):
        return f"{self.keyword} → {self.suggestion}"
    
    @classmethod
    def get_suggestions(cls, query, category=None, limit=10):
        """자동완성 제안 가져오기"""
        suggestions = cls.objects.filter(
            keyword__istartswith=query.lower()
        )
        
        if category:
            suggestions = suggestions.filter(category=category)
        
        return suggestions[:limit]