# -*- coding: utf-8 -*-
from django.urls import path
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def test_api(request):
    """테스트 API"""
    return Response({
        'message': '한글 테스트: 가나다라마바사',
        'timestamp': '2024년 12월',
        'status': 'success'
    })

app_name = 'main'
urlpatterns = [
    path('test/', test_api, name='test_api'),
]
