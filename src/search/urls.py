from django.urls import path
from . import views

app_name = 'search'

urlpatterns = [
    # 통합 검색
    path('', views.unified_search, name='unified_search'),
    
    # 자동완성
    path('autocomplete/', views.autocomplete, name='autocomplete'),
    
    # 검색 기록
    path('history/', views.search_history, name='search_history'),
    path('history/clear/', views.clear_search_history, name='clear_search_history'),
    
    # 인기 검색어
    path('trending/', views.trending_searches, name='trending_searches'),
    
    # 저장된 검색 필터
    path('saved/', views.saved_searches, name='saved_searches'),
    path('saved/save/', views.save_search, name='save_search'),
    path('saved/<int:search_id>/', views.manage_saved_search, name='manage_saved_search'),
    path('saved/<int:search_id>/apply/', views.apply_saved_search, name='apply_saved_search'),
    
    # 인덱싱
    path('index/', views.index_content, name='index_content'),
    
    # 고급 필터
    path('filter/', views.advanced_filter, name='advanced_filter'),
]