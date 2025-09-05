"""
OneSquare 사진 업로드 및 처리 API 뷰

현장 사진 업로드, 압축, 썸네일 생성, 배치 처리 기능
"""

import json
import uuid
from datetime import datetime
from io import BytesIO
from PIL import Image, ExifTags
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings
from django.db import transaction
import logging

from .models import WorkReport, ReportPhoto

logger = logging.getLogger(__name__)


class PhotoUploadAPI:
    """사진 업로드 API 클래스"""
    
    @staticmethod
    def extract_exif_data(image_file):
        """EXIF 데이터 추출"""
        try:
            image = Image.open(image_file)
            exif_data = {}
            
            if hasattr(image, '_getexif'):
                exif = image._getexif()
                if exif:
                    for tag_id, value in exif.items():
                        tag = ExifTags.TAGS.get(tag_id, tag_id)
                        exif_data[tag] = value
            
            # GPS 정보 추출
            gps_data = PhotoUploadAPI.extract_gps_data(exif_data)
            if gps_data:
                exif_data['GPS'] = gps_data
            
            return exif_data
        except Exception as e:
            logger.warning(f"Failed to extract EXIF data: {e}")
            return {}

    @staticmethod
    def extract_gps_data(exif_data):
        """GPS 데이터 추출 및 변환"""
        try:
            if 'GPSInfo' not in exif_data:
                return None
                
            gps_info = exif_data['GPSInfo']
            
            def convert_to_degrees(value):
                """GPS 좌표를 도 단위로 변환"""
                d, m, s = value
                return d + (m / 60.0) + (s / 3600.0)
            
            gps_data = {}
            
            if 2 in gps_info and 4 in gps_info:  # 위도, 경도
                lat = convert_to_degrees(gps_info[2])
                lon = convert_to_degrees(gps_info[4])
                
                # 남북, 동서 방향 확인
                if gps_info.get(1) == 'S':
                    lat = -lat
                if gps_info.get(3) == 'W':
                    lon = -lon
                    
                gps_data['latitude'] = lat
                gps_data['longitude'] = lon
            
            if 6 in gps_info:  # 고도
                gps_data['altitude'] = float(gps_info[6])
            
            return gps_data
            
        except Exception as e:
            logger.warning(f"Failed to extract GPS data: {e}")
            return None

    @staticmethod
    def compress_image(image_file, max_width=1920, max_height=1080, quality=85):
        """이미지 압축"""
        try:
            image = Image.open(image_file)
            
            # EXIF 방향 정보에 따른 회전 처리
            try:
                for orientation in ExifTags.TAGS.keys():
                    if ExifTags.TAGS[orientation] == 'Orientation':
                        break
                
                exif = image._getexif()
                if exif is not None:
                    orientation_value = exif.get(orientation)
                    if orientation_value == 3:
                        image = image.rotate(180, expand=True)
                    elif orientation_value == 6:
                        image = image.rotate(270, expand=True)
                    elif orientation_value == 8:
                        image = image.rotate(90, expand=True)
            except (AttributeError, KeyError, TypeError):
                pass
            
            # 크기 조정
            original_width, original_height = image.size
            
            if original_width > max_width or original_height > max_height:
                ratio = min(max_width / original_width, max_height / original_height)
                new_width = int(original_width * ratio)
                new_height = int(original_height * ratio)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # RGB로 변환 (JPEG 저장을 위해)
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')
            
            # 압축된 이미지를 메모리에 저장
            output = BytesIO()
            image.save(output, format='JPEG', quality=quality, optimize=True)
            output.seek(0)
            
            return ContentFile(output.read(), name=f'compressed_{uuid.uuid4().hex}.jpg')
            
        except Exception as e:
            logger.error(f"Image compression failed: {e}")
            raise

    @staticmethod
    def generate_thumbnail(image_file, size=150):
        """썸네일 생성"""
        try:
            image = Image.open(image_file)
            
            # 정사각형 썸네일 생성 (crop)
            width, height = image.size
            min_dimension = min(width, height)
            
            # 중앙을 기준으로 정사각형 영역 추출
            left = (width - min_dimension) // 2
            top = (height - min_dimension) // 2
            right = left + min_dimension
            bottom = top + min_dimension
            
            image = image.crop((left, top, right, bottom))
            image = image.resize((size, size), Image.Resampling.LANCZOS)
            
            # RGB로 변환
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')
            
            # 썸네일을 메모리에 저장
            output = BytesIO()
            image.save(output, format='JPEG', quality=70, optimize=True)
            output.seek(0)
            
            return ContentFile(output.read(), name=f'thumb_{uuid.uuid4().hex}.jpg')
            
        except Exception as e:
            logger.error(f"Thumbnail generation failed: {e}")
            raise


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def upload_photo(request):
    """단일 사진 업로드"""
    try:
        # 파일 검증
        if 'original_image' not in request.FILES:
            return JsonResponse({'error': 'Original image is required'}, status=400)
        
        original_file = request.FILES['original_image']
        
        # 파일 크기 제한 (10MB)
        if original_file.size > 10 * 1024 * 1024:
            return JsonResponse({'error': 'File size too large (max 10MB)'}, status=400)
        
        # 파일 형식 검증
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
        if original_file.content_type not in allowed_types:
            return JsonResponse({'error': 'Unsupported file type'}, status=400)
        
        # 요청 데이터 추출
        photo_type = request.POST.get('photo_type', 'other')
        caption = request.POST.get('caption', '')
        metadata_str = request.POST.get('metadata', '{}')
        
        try:
            metadata = json.loads(metadata_str)
        except json.JSONDecodeError:
            metadata = {}
        
        # 현재 활성 리포트 찾기 (임시로 생성)
        report = WorkReport.objects.filter(
            session__user=request.user,
            status='draft'
        ).first()
        
        if not report:
            return JsonResponse({'error': 'No active report found'}, status=400)
        
        with transaction.atomic():
            # EXIF 데이터 추출
            original_file.seek(0)
            exif_data = PhotoUploadAPI.extract_exif_data(original_file)
            
            # 이미지 압축
            original_file.seek(0)
            compressed_file = PhotoUploadAPI.compress_image(original_file)
            
            # 썸네일 생성
            original_file.seek(0)
            thumbnail_file = PhotoUploadAPI.generate_thumbnail(original_file)
            
            # GPS 정보 추출 (EXIF 또는 메타데이터에서)
            latitude = None
            longitude = None
            taken_at = None
            
            # EXIF GPS 정보 우선
            if 'GPS' in exif_data:
                latitude = exif_data['GPS'].get('latitude')
                longitude = exif_data['GPS'].get('longitude')
            
            # 메타데이터 GPS 정보 사용 (EXIF가 없는 경우)
            if not latitude and 'location' in metadata:
                latitude = metadata['location'].get('latitude')
                longitude = metadata['location'].get('longitude')
            
            # 촬영 시간 추출
            if 'DateTime' in exif_data:
                try:
                    taken_at = datetime.strptime(exif_data['DateTime'], '%Y:%m:%d %H:%M:%S')
                except (ValueError, TypeError):
                    pass
            
            # 사진 객체 생성
            photo = ReportPhoto.objects.create(
                report=report,
                original_image=original_file,
                compressed_image=compressed_file,
                thumbnail=thumbnail_file,
                photo_type=photo_type,
                caption=caption,
                latitude=latitude,
                longitude=longitude,
                taken_at=taken_at,
                original_file_size=original_file.size,
                compressed_file_size=len(compressed_file.read())
            )
            
            logger.info(f"Photo uploaded successfully: {photo.id} by user {request.user.id}")
            
            return JsonResponse({
                'success': True,
                'photo_id': str(photo.id),
                'compressed_size': photo.compressed_file_size,
                'compression_ratio': photo.compression_ratio,
                'thumbnail_url': photo.thumbnail.url if photo.thumbnail else None,
                'message': 'Photo uploaded successfully'
            })
    
    except Exception as e:
        logger.error(f"Photo upload failed: {e}")
        return JsonResponse({'error': 'Upload failed', 'detail': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def batch_upload_photos(request):
    """배치 사진 업로드"""
    try:
        if not request.FILES:
            return JsonResponse({'error': 'No files uploaded'}, status=400)
        
        # 현재 활성 리포트 찾기
        report = WorkReport.objects.filter(
            session__user=request.user,
            status='draft'
        ).first()
        
        if not report:
            return JsonResponse({'error': 'No active report found'}, status=400)
        
        results = []
        successful_uploads = 0
        failed_uploads = 0
        
        # 각 파일에 대해 업로드 처리
        for field_name, uploaded_file in request.FILES.items():
            try:
                # 파일 크기 및 형식 검증
                if uploaded_file.size > 10 * 1024 * 1024:
                    results.append({
                        'file': field_name,
                        'success': False,
                        'error': 'File size too large'
                    })
                    failed_uploads += 1
                    continue
                
                # 개별 파일 업로드 처리 (upload_photo 로직 재사용)
                with transaction.atomic():
                    # EXIF 데이터 추출
                    exif_data = PhotoUploadAPI.extract_exif_data(uploaded_file)
                    
                    # 이미지 압축 및 썸네일 생성
                    uploaded_file.seek(0)
                    compressed_file = PhotoUploadAPI.compress_image(uploaded_file)
                    
                    uploaded_file.seek(0)
                    thumbnail_file = PhotoUploadAPI.generate_thumbnail(uploaded_file)
                    
                    # GPS 정보 추출
                    latitude = None
                    longitude = None
                    if 'GPS' in exif_data:
                        latitude = exif_data['GPS'].get('latitude')
                        longitude = exif_data['GPS'].get('longitude')
                    
                    # 사진 객체 생성
                    photo = ReportPhoto.objects.create(
                        report=report,
                        original_image=uploaded_file,
                        compressed_image=compressed_file,
                        thumbnail=thumbnail_file,
                        photo_type='other',  # 기본값
                        original_file_size=uploaded_file.size,
                        compressed_file_size=len(compressed_file.read())
                    )
                    
                    results.append({
                        'file': field_name,
                        'success': True,
                        'photo_id': str(photo.id),
                        'compressed_size': photo.compressed_file_size,
                        'compression_ratio': photo.compression_ratio
                    })
                    successful_uploads += 1
            
            except Exception as e:
                logger.error(f"Failed to upload {field_name}: {e}")
                results.append({
                    'file': field_name,
                    'success': False,
                    'error': str(e)
                })
                failed_uploads += 1
        
        logger.info(f"Batch upload completed: {successful_uploads} success, {failed_uploads} failed")
        
        return JsonResponse({
            'success': True,
            'total_files': len(request.FILES),
            'successful_uploads': successful_uploads,
            'failed_uploads': failed_uploads,
            'results': results
        })
    
    except Exception as e:
        logger.error(f"Batch upload failed: {e}")
        return JsonResponse({'error': 'Batch upload failed', 'detail': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def upload_progress(request):
    """업로드 진행상황 조회"""
    try:
        session_id = request.GET.get('session_id')
        if not session_id:
            return JsonResponse({'error': 'Session ID required'}, status=400)
        
        # 캐시나 데이터베이스에서 진행상황 조회
        # 실제 구현에서는 Redis나 캐시를 사용
        progress_data = {
            'session_id': session_id,
            'total_files': 0,
            'uploaded_files': 0,
            'failed_files': 0,
            'current_file': None,
            'overall_progress': 0,
            'status': 'idle'  # idle, uploading, completed, failed
        }
        
        return JsonResponse(progress_data)
    
    except Exception as e:
        logger.error(f"Failed to get upload progress: {e}")
        return JsonResponse({'error': 'Failed to get progress'}, status=500)


@login_required
@require_http_methods(["GET"])
def photo_list(request):
    """사진 목록 조회"""
    try:
        # 현재 사용자의 최근 사진들 조회
        photos = ReportPhoto.objects.filter(
            report__session__user=request.user
        ).order_by('-created_at')[:50]
        
        photo_data = []
        for photo in photos:
            photo_data.append({
                'id': str(photo.id),
                'type': photo.photo_type,
                'type_display': photo.get_photo_type_display(),
                'caption': photo.caption,
                'thumbnail_url': photo.thumbnail.url if photo.thumbnail else None,
                'compressed_url': photo.compressed_image.url if photo.compressed_image else None,
                'original_size': photo.original_file_size,
                'compressed_size': photo.compressed_file_size,
                'compression_ratio': photo.compression_ratio,
                'created_at': photo.created_at.isoformat(),
                'report_id': str(photo.report.id) if photo.report else None
            })
        
        return JsonResponse({
            'success': True,
            'photos': photo_data,
            'total_count': len(photo_data)
        })
    
    except Exception as e:
        logger.error(f"Failed to get photo list: {e}")
        return JsonResponse({'error': 'Failed to get photo list'}, status=500)


@login_required
@require_http_methods(["DELETE"])
def delete_photo(request, photo_id):
    """사진 삭제"""
    try:
        photo = ReportPhoto.objects.get(
            id=photo_id,
            report__session__user=request.user
        )
        
        # 파일 삭제
        if photo.original_image:
            default_storage.delete(photo.original_image.name)
        if photo.compressed_image:
            default_storage.delete(photo.compressed_image.name)
        if photo.thumbnail:
            default_storage.delete(photo.thumbnail.name)
        
        photo.delete()
        
        logger.info(f"Photo deleted: {photo_id} by user {request.user.id}")
        
        return JsonResponse({
            'success': True,
            'message': 'Photo deleted successfully'
        })
    
    except ReportPhoto.DoesNotExist:
        return JsonResponse({'error': 'Photo not found'}, status=404)
    except Exception as e:
        logger.error(f"Failed to delete photo {photo_id}: {e}")
        return JsonResponse({'error': 'Failed to delete photo'}, status=500)


@login_required
@require_http_methods(["GET"])
def photo_stats(request):
    """사진 업로드 통계"""
    try:
        # 사용자별 통계 계산
        photos = ReportPhoto.objects.filter(report__session__user=request.user)
        
        total_photos = photos.count()
        total_original_size = sum(p.original_file_size or 0 for p in photos)
        total_compressed_size = sum(p.compressed_file_size or 0 for p in photos)
        
        avg_compression_ratio = 0
        if total_original_size > 0:
            avg_compression_ratio = round((1 - total_compressed_size / total_original_size) * 100, 2)
        
        # 타입별 분포
        type_distribution = {}
        for photo in photos:
            photo_type = photo.get_photo_type_display()
            type_distribution[photo_type] = type_distribution.get(photo_type, 0) + 1
        
        return JsonResponse({
            'success': True,
            'stats': {
                'total_photos': total_photos,
                'total_original_size': total_original_size,
                'total_compressed_size': total_compressed_size,
                'avg_compression_ratio': avg_compression_ratio,
                'storage_saved': total_original_size - total_compressed_size,
                'type_distribution': type_distribution
            }
        })
    
    except Exception as e:
        logger.error(f"Failed to get photo stats: {e}")
        return JsonResponse({'error': 'Failed to get stats'}, status=500)