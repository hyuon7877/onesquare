"""Field Reports Photo Views 모듈

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
