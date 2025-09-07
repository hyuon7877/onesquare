"""
OneSquare 재고 관리 API 뷰

현장 비품 재고 체크 및 관리 기능
"""

import json
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum
from django.db import transaction
from django.conf import settings
import logging

from .models import InventoryItem, InventoryCheck, WorkReport, WorkSession, FieldSite

logger = logging.getLogger(__name__)


class InventoryAPI:
    """재고 관리 API 클래스"""
    
    @staticmethod
    def calculate_stock_status(current_quantity, minimum_stock):
        """재고 상태 계산"""
        if current_quantity == 0:
            return 'out_of_stock', '품절'
        elif current_quantity < minimum_stock:
            return 'low_stock', '부족'
        else:
            return 'sufficient', '충분'
    
    @staticmethod
    def get_replenishment_priority(item, current_quantity):
        """보충 우선순위 계산"""
        if current_quantity == 0:
            return 1  # 최고 우선순위
        
        shortage_ratio = (item.minimum_stock - current_quantity) / item.minimum_stock
        
        if shortage_ratio >= 0.8:
            return 2  # 높은 우선순위
        elif shortage_ratio >= 0.5:
            return 3  # 중간 우선순위
        else:
            return 4  # 낮은 우선순위


@login_required
@require_http_methods(["GET"])
def inventory_items(request):
    """재고 항목 목록 조회"""
    try:
        # 필터링 파라미터
        category = request.GET.get('category', '')
        search = request.GET.get('search', '')
        status = request.GET.get('status', '')  # all, low_stock, out_of_stock
        
        # 기본 쿼리
        items_query = InventoryItem.objects.filter(is_active=True)
        
        # 카테고리 필터
        if category and category != 'all':
            items_query = items_query.filter(category=category)
        
        # 검색 필터
        if search:
            items_query = items_query.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(description__icontains=search)
            )
        
        # 정렬
        items_query = items_query.order_by('category', 'name')
        
        # 페이징
        page = request.GET.get('page', 1)
        per_page = int(request.GET.get('per_page', 50))
        
        paginator = Paginator(items_query, per_page)
        items_page = paginator.get_page(page)
        
        # 데이터 변환
        items_data = []
        for item in items_page:
            # 최근 재고 체크 정보
            latest_check = InventoryCheck.objects.filter(
                item=item,
                report__session__user=request.user
            ).order_by('-checked_at').first()
            
            current_quantity = latest_check.current_quantity if latest_check else 0
            status_code, status_display = InventoryAPI.calculate_stock_status(
                current_quantity, item.minimum_stock
            )
            
            item_data = {
                'id': str(item.id),
                'name': item.name,
                'code': item.code,
                'category': item.category,
                'categoryDisplay': item.get_category_display(),
                'unit': item.get_unit_display(),
                'description': item.description,
                'minimumStock': item.minimum_stock,
                'maximumStock': item.maximum_stock,
                'currentQuantity': current_quantity,
                'status': status_code,
                'statusDisplay': status_display,
                'lastChecked': latest_check.checked_at.isoformat() if latest_check else None,
                'needsReplenishment': latest_check.needs_replenishment if latest_check else False,
                'lastNotes': latest_check.notes if latest_check else '',
            }
            
            # 상태 필터 적용
            if status == 'low_stock' and status_code != 'low_stock':
                continue
            elif status == 'out_of_stock' and status_code != 'out_of_stock':
                continue
            
            items_data.append(item_data)
        
        # 통계 정보
        total_items = items_query.count()
        low_stock_count = len([item for item in items_data if item['status'] == 'low_stock'])
        out_of_stock_count = len([item for item in items_data if item['status'] == 'out_of_stock'])
        
        return JsonResponse({
            'success': True,
            'items': items_data,
            'pagination': {
                'current_page': items_page.number,
                'total_pages': paginator.num_pages,
                'total_items': total_items,
                'per_page': per_page,
                'has_next': items_page.has_next(),
                'has_previous': items_page.has_previous()
            },
            'stats': {
                'total_items': total_items,
                'low_stock_items': low_stock_count,
                'out_of_stock_items': out_of_stock_count,
                'sufficient_items': total_items - low_stock_count - out_of_stock_count
            }
        })
    
    except Exception as e:
        logger.error(f"Failed to get inventory items: {e}")
        return JsonResponse({'error': 'Failed to get inventory items'}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def save_inventory_check(request):
    """단일 재고 체크 저장"""
    try:
        data = json.loads(request.body)
        
        item_id = data.get('item_id')
        current_quantity = data.get('current_quantity', 0)
        required_quantity = data.get('required_quantity')
        notes = data.get('notes', '')
        
        if not item_id:
            return JsonResponse({'error': 'Item ID is required'}, status=400)
        
        # 재고 항목 확인
        try:
            item = InventoryItem.objects.get(id=item_id, is_active=True)
        except InventoryItem.DoesNotExist:
            return JsonResponse({'error': 'Inventory item not found'}, status=404)
        
        # 현재 활성 리포트 찾기
        active_session = WorkSession.objects.filter(
            user=request.user,
            status__in=['started', 'paused', 'resumed']
        ).first()
        
        if not active_session:
            return JsonResponse({'error': 'No active work session found'}, status=400)
        
        # 리포트 찾기 또는 생성
        report, created = WorkReport.objects.get_or_create(
            session=active_session,
            defaults={
                'title': f'{active_session.site.name} 재고 체크',
                'status': 'draft'
            }
        )
        
        with transaction.atomic():
            # 재고 체크 생성 또는 업데이트
            inventory_check, check_created = InventoryCheck.objects.update_or_create(
                report=report,
                item=item,
                defaults={
                    'current_quantity': current_quantity,
                    'required_quantity': required_quantity,
                    'notes': notes
                }
            )
            
            # 상태 계산 (모델의 save 메서드에서 자동 처리됨)
            status_code, status_display = InventoryAPI.calculate_stock_status(
                current_quantity, item.minimum_stock
            )
            
            logger.info(
                f"Inventory check saved: {item.name} - {current_quantity} {item.unit} "
                f"by user {request.user.id}"
            )
            
            return JsonResponse({
                'success': True,
                'check_id': str(inventory_check.id),
                'status': status_code,
                'status_display': status_display,
                'is_sufficient': inventory_check.is_sufficient,
                'needs_replenishment': inventory_check.needs_replenishment,
                'message': f'{item.name} 재고 체크가 저장되었습니다.'
            })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Failed to save inventory check: {e}")
        return JsonResponse({'error': 'Failed to save inventory check'}, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def save_all_inventory_checks(request):
    """배치 재고 체크 저장"""
    try:
        data = json.loads(request.body)
        checks_data = data.get('checks', {})
        
        if not checks_data:
            return JsonResponse({'error': 'No checks data provided'}, status=400)
        
        # 현재 활성 리포트 찾기
        active_session = WorkSession.objects.filter(
            user=request.user,
            status__in=['started', 'paused', 'resumed']
        ).first()
        
        if not active_session:
            return JsonResponse({'error': 'No active work session found'}, status=400)
        
        # 리포트 찾기 또는 생성
        report, created = WorkReport.objects.get_or_create(
            session=active_session,
            defaults={
                'title': f'{active_session.site.name} 재고 체크',
                'status': 'draft'
            }
        )
        
        saved_checks = []
        failed_checks = []
        
        with transaction.atomic():
            for item_id, check_data in checks_data.items():
                try:
                    # 재고 항목 확인
                    item = InventoryItem.objects.get(id=item_id, is_active=True)
                    
                    current_quantity = int(check_data.get('currentQuantity', 0))
                    required_quantity = int(check_data.get('requiredQuantity', 0))
                    notes = check_data.get('notes', '')
                    
                    # 재고 체크 생성 또는 업데이트
                    inventory_check, check_created = InventoryCheck.objects.update_or_create(
                        report=report,
                        item=item,
                        defaults={
                            'current_quantity': current_quantity,
                            'required_quantity': required_quantity,
                            'notes': notes
                        }
                    )
                    
                    status_code, status_display = InventoryAPI.calculate_stock_status(
                        current_quantity, item.minimum_stock
                    )
                    
                    saved_checks.append({
                        'item_id': item_id,
                        'item_name': item.name,
                        'current_quantity': current_quantity,
                        'status': status_code,
                        'status_display': status_display,
                        'is_sufficient': inventory_check.is_sufficient,
                        'needs_replenishment': inventory_check.needs_replenishment
                    })
                    
                except InventoryItem.DoesNotExist:
                    failed_checks.append({
                        'item_id': item_id,
                        'error': 'Item not found'
                    })
                except Exception as e:
                    failed_checks.append({
                        'item_id': item_id,
                        'error': str(e)
                    })
        
        logger.info(
            f"Batch inventory check saved: {len(saved_checks)} success, "
            f"{len(failed_checks)} failed by user {request.user.id}"
        )
        
        return JsonResponse({
            'success': True,
            'saved_count': len(saved_checks),
            'failed_count': len(failed_checks),
            'saved_checks': saved_checks,
            'failed_checks': failed_checks,
            'message': f'{len(saved_checks)}개 항목의 재고 체크가 저장되었습니다.'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Failed to save batch inventory checks: {e}")
        return JsonResponse({'error': 'Failed to save inventory checks'}, status=500)


@login_required
@require_http_methods(["GET"])
def inventory_stats(request):
    """재고 통계 조회"""
    try:
        # 시간 범위 필터
        days = int(request.GET.get('days', 7))
        start_date = datetime.now() - timedelta(days=days)
        
        # 기본 통계
        total_items = InventoryItem.objects.filter(is_active=True).count()
        
        # 최근 체크된 항목들
        recent_checks = InventoryCheck.objects.filter(
            report__session__user=request.user,
            checked_at__gte=start_date
        ).select_related('item', 'report')
        
        # 상태별 통계
        stats = {
            'total_items': total_items,
            'checked_items': recent_checks.count(),
            'sufficient': 0,
            'low_stock': 0,
            'out_of_stock': 0,
            'needs_replenishment': recent_checks.filter(needs_replenishment=True).count()
        }
        
        # 각 체크의 상태 분류
        for check in recent_checks:
            status_code, _ = InventoryAPI.calculate_stock_status(
                check.current_quantity, check.item.minimum_stock
            )
            stats[status_code] = stats.get(status_code, 0) + 1
        
        # 카테고리별 통계
        category_stats = {}
        categories = InventoryItem.ITEM_CATEGORY_CHOICES
        
        for category_code, category_name in categories:
            category_items = InventoryItem.objects.filter(
                is_active=True,
                category=category_code
            ).count()
            
            category_checked = recent_checks.filter(
                item__category=category_code
            ).count()
            
            category_stats[category_code] = {
                'name': category_name,
                'total_items': category_items,
                'checked_items': category_checked,
                'check_rate': round((category_checked / category_items * 100) if category_items > 0 else 0, 1)
            }
        
        # 최근 체크 활동
        recent_activity = []
        for check in recent_checks.order_by('-checked_at')[:10]:
            status_code, status_display = InventoryAPI.calculate_stock_status(
                check.current_quantity, check.item.minimum_stock
            )
            
            recent_activity.append({
                'item_name': check.item.name,
                'current_quantity': check.current_quantity,
                'status': status_code,
                'status_display': status_display,
                'checked_at': check.checked_at.isoformat(),
                'site_name': check.report.session.site.name
            })
        
        # 보충 필요 항목들
        replenishment_needed = []
        for check in recent_checks.filter(needs_replenishment=True).order_by('current_quantity'):
            priority = InventoryAPI.get_replenishment_priority(check.item, check.current_quantity)
            
            replenishment_needed.append({
                'item_name': check.item.name,
                'item_code': check.item.code,
                'current_quantity': check.current_quantity,
                'minimum_stock': check.item.minimum_stock,
                'required_quantity': check.required_quantity,
                'unit': check.item.get_unit_display(),
                'priority': priority,
                'shortage_amount': max(0, check.item.minimum_stock - check.current_quantity),
                'last_checked': check.checked_at.isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'period_days': days,
            'stats': stats,
            'category_stats': category_stats,
            'recent_activity': recent_activity,
            'replenishment_needed': replenishment_needed
        })
    
    except Exception as e:
        logger.error(f"Failed to get inventory stats: {e}")
        return JsonResponse({'error': 'Failed to get inventory stats'}, status=500)


@login_required
@require_http_methods(["GET"])
def low_stock_alerts(request):
    """재고 부족 알림 조회"""
    try:
        # 최근 체크된 항목들 중 재고 부족 항목
        low_stock_checks = InventoryCheck.objects.filter(
            report__session__user=request.user,
            is_sufficient=False
        ).select_related('item', 'report').order_by('-checked_at')
        
        alerts = []
        for check in low_stock_checks:
            status_code, status_display = InventoryAPI.calculate_stock_status(
                check.current_quantity, check.item.minimum_stock
            )
            
            priority = InventoryAPI.get_replenishment_priority(check.item, check.current_quantity)
            
            alerts.append({
                'id': str(check.id),
                'item_name': check.item.name,
                'item_code': check.item.code,
                'category': check.item.get_category_display(),
                'current_quantity': check.current_quantity,
                'minimum_stock': check.item.minimum_stock,
                'unit': check.item.get_unit_display(),
                'status': status_code,
                'status_display': status_display,
                'priority': priority,
                'shortage_amount': max(0, check.item.minimum_stock - check.current_quantity),
                'last_checked': check.checked_at.isoformat(),
                'site_name': check.report.session.site.name,
                'notes': check.notes,
                'alert_level': 'critical' if status_code == 'out_of_stock' else 'warning'
            })
        
        # 우선순위별 정렬
        alerts.sort(key=lambda x: (x['priority'], -x['shortage_amount']))
        
        return JsonResponse({
            'success': True,
            'alerts': alerts,
            'total_alerts': len(alerts),
            'critical_alerts': len([a for a in alerts if a['alert_level'] == 'critical']),
            'warning_alerts': len([a for a in alerts if a['alert_level'] == 'warning'])
        })
    
    except Exception as e:
        logger.error(f"Failed to get low stock alerts: {e}")
        return JsonResponse({'error': 'Failed to get low stock alerts'}, status=500)


@login_required
@require_http_methods(["GET"])
def inventory_history(request):
    """재고 체크 히스토리 조회"""
    try:
        item_id = request.GET.get('item_id')
        days = int(request.GET.get('days', 30))
        
        if not item_id:
            return JsonResponse({'error': 'Item ID is required'}, status=400)
        
        # 재고 항목 확인
        try:
            item = InventoryItem.objects.get(id=item_id, is_active=True)
        except InventoryItem.DoesNotExist:
            return JsonResponse({'error': 'Inventory item not found'}, status=404)
        
        # 히스토리 조회
        start_date = datetime.now() - timedelta(days=days)
        history = InventoryCheck.objects.filter(
            item=item,
            report__session__user=request.user,
            checked_at__gte=start_date
        ).select_related('report__session__site').order_by('-checked_at')
        
        history_data = []
        for check in history:
            status_code, status_display = InventoryAPI.calculate_stock_status(
                check.current_quantity, item.minimum_stock
            )
            
            history_data.append({
                'id': str(check.id),
                'current_quantity': check.current_quantity,
                'required_quantity': check.required_quantity,
                'status': status_code,
                'status_display': status_display,
                'is_sufficient': check.is_sufficient,
                'needs_replenishment': check.needs_replenishment,
                'notes': check.notes,
                'checked_at': check.checked_at.isoformat(),
                'site_name': check.report.session.site.name,
                'report_id': str(check.report.id)
            })
        
        return JsonResponse({
            'success': True,
            'item': {
                'id': str(item.id),
                'name': item.name,
                'code': item.code,
                'category': item.get_category_display(),
                'unit': item.get_unit_display(),
                'minimum_stock': item.minimum_stock,
                'maximum_stock': item.maximum_stock
            },
            'history': history_data,
            'period_days': days
        })
    
    except Exception as e:
        logger.error(f"Failed to get inventory history: {e}")
        return JsonResponse({'error': 'Failed to get inventory history'}, status=500)