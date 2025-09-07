"""사진 관리 API 뷰"""
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
