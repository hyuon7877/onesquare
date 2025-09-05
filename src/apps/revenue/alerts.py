"""
OneSquare 매출 관리 - 알림 및 대시보드 통합 시스템
실시간 알림, 목표 달성 알림, 연체 알림 등 포함
"""

import logging
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum, Q, Count
from django.core.cache import cache
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from typing import Dict, List, Optional, Tuple

from .models import RevenueRecord, RevenueTarget, RevenueAlert, Client, Project
from .permissions import RevenuePermissionManager, UserRole

logger = logging.getLogger(__name__)

class RevenueAlertManager:
    """매출 알림 관리 시스템"""
    
    def __init__(self):
        self.alert_cache_timeout = 300  # 5분 캐시
        self.overdue_threshold_days = 30  # 연체 기준 일수
    
    def generate_all_alerts(self) -> Dict:
        """모든 유형의 알림 생성"""
        alerts = {
            'overdue_payments': self.check_overdue_payments(),
            'target_achievements': self.check_target_achievements(),
            'low_monthly_revenue': self.check_low_monthly_revenue(),
            'upcoming_deadlines': self.check_upcoming_deadlines(),
            'large_pending_amounts': self.check_large_pending_amounts(),
            'client_payment_delays': self.check_client_payment_delays()
        }
        
        # 전체 알림 개수 계산
        total_alerts = sum(len(alert_list) for alert_list in alerts.values())
        alerts['summary'] = {
            'total_count': total_alerts,
            'generated_at': timezone.now().isoformat(),
            'categories': {k: len(v) for k, v in alerts.items() if k != 'summary'}
        }
        
        logger.info(f"총 {total_alerts}개의 알림 생성 완료")
        return alerts
    
    def check_overdue_payments(self) -> List[Dict]:
        """연체 결제 확인"""
        cutoff_date = timezone.now().date() - timedelta(days=self.overdue_threshold_days)
        
        overdue_revenues = RevenueRecord.objects.filter(
            payment_status='pending',
            due_date__lt=cutoff_date,
            is_confirmed=True
        ).select_related('project', 'client').order_by('due_date')
        
        alerts = []
        for revenue in overdue_revenues:
            days_overdue = (timezone.now().date() - revenue.due_date).days
            
            alerts.append({
                'type': 'overdue_payment',
                'severity': 'high' if days_overdue > 60 else 'medium',
                'revenue_id': str(revenue.id),
                'project_name': revenue.project.name,
                'client_name': revenue.client.name,
                'amount': float(revenue.net_amount),
                'due_date': revenue.due_date.isoformat(),
                'days_overdue': days_overdue,
                'message': f"{revenue.client.name} - {revenue.project.name}: {days_overdue}일 연체 (₩{revenue.net_amount:,})",
                'action_url': f"/revenue/list/?revenue_id={revenue.id}",
                'priority': 1 if days_overdue > 60 else 2
            })
        
        # 심각도별 정렬
        alerts.sort(key=lambda x: (x['priority'], -x['days_overdue']))
        
        logger.info(f"연체 결제 알림 {len(alerts)}개 생성")
        return alerts
    
    def check_target_achievements(self) -> List[Dict]:
        """목표 달성률 확인"""
        current_date = timezone.now().date()
        current_month = current_date.replace(day=1)
        
        # 이번 달 목표들 확인
        monthly_targets = RevenueTarget.objects.filter(
            target_type='monthly',
            year=current_date.year,
            month=current_date.month
        ).prefetch_related('assigned_user')
        
        alerts = []
        for target in monthly_targets:
            achievement_rate = target.get_achievement_rate()
            
            # 월 진행도 계산 (예: 15일이면 50% 진행)
            days_in_month = (current_month.replace(month=current_month.month + 1) - current_month).days
            month_progress = (current_date.day / days_in_month) * 100
            
            # 목표 대비 진행도 분석
            if achievement_rate < month_progress - 20:  # 예상 진행도보다 20% 이상 뒤처짐
                severity = 'high' if achievement_rate < 50 else 'medium'
                
                alerts.append({
                    'type': 'target_behind',
                    'severity': severity,
                    'target_id': str(target.id),
                    'target_type': target.get_target_type_display(),
                    'assigned_user': target.assigned_user.get_full_name() if target.assigned_user else '전체',
                    'target_amount': float(target.target_amount),
                    'achievement_rate': achievement_rate,
                    'month_progress': month_progress,
                    'gap': month_progress - achievement_rate,
                    'message': f"목표 달성률 부족: {achievement_rate:.1f}% (예상: {month_progress:.1f}%)",
                    'action_url': f"/revenue/?target_id={target.id}",
                    'priority': 1 if severity == 'high' else 2
                })
            
            elif achievement_rate >= 100:  # 목표 초과 달성
                alerts.append({
                    'type': 'target_exceeded',
                    'severity': 'info',
                    'target_id': str(target.id),
                    'target_type': target.get_target_type_display(),
                    'assigned_user': target.assigned_user.get_full_name() if target.assigned_user else '전체',
                    'target_amount': float(target.target_amount),
                    'achievement_rate': achievement_rate,
                    'message': f"목표 달성 완료! {achievement_rate:.1f}% 달성",
                    'action_url': f"/revenue/?target_id={target.id}",
                    'priority': 3
                })
        
        logger.info(f"목표 달성률 알림 {len(alerts)}개 생성")
        return alerts
    
    def check_low_monthly_revenue(self) -> List[Dict]:
        """월별 매출 저조 확인"""
        current_date = timezone.now().date()
        current_month_start = current_date.replace(day=1)
        last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
        
        # 이번 달 매출
        current_revenue = RevenueRecord.objects.filter(
            revenue_date__gte=current_month_start,
            is_confirmed=True
        ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0')
        
        # 지난 달 매출
        last_revenue = RevenueRecord.objects.filter(
            revenue_date__gte=last_month_start,
            revenue_date__lt=current_month_start,
            is_confirmed=True
        ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0')
        
        alerts = []
        
        # 지난 달 대비 50% 이상 감소
        if last_revenue > 0 and current_revenue < last_revenue * Decimal('0.5'):
            decrease_rate = float((last_revenue - current_revenue) / last_revenue * 100)
            
            alerts.append({
                'type': 'low_monthly_revenue',
                'severity': 'high',
                'current_revenue': float(current_revenue),
                'last_revenue': float(last_revenue),
                'decrease_rate': decrease_rate,
                'message': f"이번 달 매출이 지난 달 대비 {decrease_rate:.1f}% 감소",
                'action_url': "/revenue/analytics/",
                'priority': 1
            })
        
        logger.info(f"월별 매출 저조 알림 {len(alerts)}개 생성")
        return alerts
    
    def check_upcoming_deadlines(self) -> List[Dict]:
        """다가오는 결제 마감일 확인"""
        today = timezone.now().date()
        warning_date = today + timedelta(days=7)  # 7일 후까지
        
        upcoming_revenues = RevenueRecord.objects.filter(
            payment_status='pending',
            due_date__gte=today,
            due_date__lte=warning_date,
            is_confirmed=True
        ).select_related('project', 'client').order_by('due_date')
        
        alerts = []
        for revenue in upcoming_revenues:
            days_until_due = (revenue.due_date - today).days
            
            severity = 'high' if days_until_due <= 3 else 'medium'
            
            alerts.append({
                'type': 'upcoming_deadline',
                'severity': severity,
                'revenue_id': str(revenue.id),
                'project_name': revenue.project.name,
                'client_name': revenue.client.name,
                'amount': float(revenue.net_amount),
                'due_date': revenue.due_date.isoformat(),
                'days_until_due': days_until_due,
                'message': f"{revenue.client.name}: {days_until_due}일 후 결제 예정 (₩{revenue.net_amount:,})",
                'action_url': f"/revenue/list/?revenue_id={revenue.id}",
                'priority': 1 if days_until_due <= 3 else 2
            })
        
        logger.info(f"다가오는 마감일 알림 {len(alerts)}개 생성")
        return alerts
    
    def check_large_pending_amounts(self) -> List[Dict]:
        """큰 금액의 미수금 확인"""
        threshold_amount = Decimal('10000000')  # 1천만원 이상
        
        large_pending = RevenueRecord.objects.filter(
            payment_status='pending',
            net_amount__gte=threshold_amount,
            is_confirmed=True
        ).select_related('project', 'client').order_by('-net_amount')
        
        alerts = []
        for revenue in large_pending:
            days_pending = (timezone.now().date() - revenue.revenue_date).days
            
            alerts.append({
                'type': 'large_pending_amount',
                'severity': 'medium',
                'revenue_id': str(revenue.id),
                'project_name': revenue.project.name,
                'client_name': revenue.client.name,
                'amount': float(revenue.net_amount),
                'revenue_date': revenue.revenue_date.isoformat(),
                'days_pending': days_pending,
                'message': f"큰 금액 미수금: {revenue.client.name} ₩{revenue.net_amount:,} ({days_pending}일 경과)",
                'action_url': f"/revenue/list/?revenue_id={revenue.id}",
                'priority': 2
            })
        
        logger.info(f"큰 금액 미수금 알림 {len(alerts)}개 생성")
        return alerts
    
    def check_client_payment_delays(self) -> List[Dict]:
        """고객별 결제 지연 패턴 분석"""
        # 각 고객별 평균 결제 지연 일수 계산
        clients_with_delays = Client.objects.filter(
            is_active=True,
            revenue_records__payment_status__in=['pending', 'overdue']
        ).distinct()
        
        alerts = []
        
        for client in clients_with_delays:
            # 해당 고객의 최근 6개월 결제 기록 분석
            six_months_ago = timezone.now().date() - timedelta(days=180)
            
            client_revenues = RevenueRecord.objects.filter(
                client=client,
                revenue_date__gte=six_months_ago
            ).order_by('-revenue_date')
            
            total_revenues = client_revenues.count()
            delayed_revenues = client_revenues.filter(
                Q(payment_status='overdue') | 
                (Q(payment_status='pending') & Q(due_date__lt=timezone.now().date()))
            ).count()
            
            if total_revenues > 0:
                delay_rate = (delayed_revenues / total_revenues) * 100
                
                if delay_rate > 50:  # 50% 이상 지연
                    pending_amount = client_revenues.filter(
                        payment_status='pending'
                    ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0')
                    
                    alerts.append({
                        'type': 'client_payment_pattern',
                        'severity': 'medium',
                        'client_id': client.id,
                        'client_name': client.name,
                        'delay_rate': delay_rate,
                        'total_revenues': total_revenues,
                        'delayed_revenues': delayed_revenues,
                        'pending_amount': float(pending_amount),
                        'message': f"{client.name}: 결제 지연율 {delay_rate:.1f}% (미수금 ₩{pending_amount:,})",
                        'action_url': f"/revenue/list/?client={client.code}",
                        'priority': 2
                    })
        
        logger.info(f"고객별 결제 지연 알림 {len(alerts)}개 생성")
        return alerts
    
    def get_user_specific_alerts(self, user: User) -> Dict:
        """사용자별 맞춤 알림 조회"""
        user_role = RevenuePermissionManager.get_user_role(user)
        
        # 모든 알림 생성
        all_alerts = self.generate_all_alerts()
        
        # 사용자 권한에 따른 필터링
        filtered_alerts = self._filter_alerts_by_permission(all_alerts, user, user_role)
        
        return {
            'alerts': filtered_alerts,
            'user_role': user_role,
            'permission_level': self._get_permission_level(user_role),
            'summary': all_alerts['summary']
        }
    
    def _filter_alerts_by_permission(self, alerts: Dict, user: User, user_role: str) -> Dict:
        """권한에 따른 알림 필터링"""
        filtered = {}
        
        # 최고관리자와 관리자는 모든 알림 확인 가능
        if user_role in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
            return alerts
        
        # 중간관리자는 제한적 알림만
        elif user_role == UserRole.MIDDLE_MANAGER:
            # 자신이 담당하는 프로젝트/고객 관련 알림만
            user_projects = Project.objects.filter(
                Q(project_manager=user) | Q(team_members=user)
            ).values_list('id', flat=True)
            
            for alert_type, alert_list in alerts.items():
                if alert_type == 'summary':
                    continue
                    
                filtered_list = []
                for alert in alert_list:
                    # 프로젝트 관련 알림인 경우 권한 확인
                    if 'revenue_id' in alert:
                        try:
                            revenue = RevenueRecord.objects.get(id=alert['revenue_id'])
                            if revenue.project.id in user_projects:
                                filtered_list.append(alert)
                        except RevenueRecord.DoesNotExist:
                            pass
                    else:
                        # 전체 통계성 알림은 제한적으로 표시
                        if alert_type in ['low_monthly_revenue', 'target_achievements']:
                            filtered_list.append(alert)
                
                filtered[alert_type] = filtered_list
        
        # 팀원은 본인 관련 알림만
        elif user_role == UserRole.TEAM_MEMBER:
            for alert_type, alert_list in alerts.items():
                if alert_type == 'summary':
                    continue
                    
                filtered_list = []
                for alert in alert_list:
                    # 본인이 영업담당자인 매출 관련 알림만
                    if 'revenue_id' in alert:
                        try:
                            revenue = RevenueRecord.objects.get(id=alert['revenue_id'])
                            if revenue.sales_person == user:
                                filtered_list.append(alert)
                        except RevenueRecord.DoesNotExist:
                            pass
                    # 본인 목표 관련 알림
                    elif alert_type == 'target_achievements' and 'assigned_user' in alert:
                        if alert['assigned_user'] == user.get_full_name():
                            filtered_list.append(alert)
                
                filtered[alert_type] = filtered_list
        
        # 다른 역할들은 최소 알림만
        else:
            filtered = {alert_type: [] for alert_type in alerts.keys() if alert_type != 'summary'}
        
        return filtered
    
    def _get_permission_level(self, user_role: str) -> str:
        """권한 레벨 반환"""
        levels = {
            UserRole.SUPER_ADMIN: 'full',
            UserRole.ADMIN: 'full',
            UserRole.MIDDLE_MANAGER: 'limited',
            UserRole.TEAM_MEMBER: 'minimal',
            UserRole.PARTNER: 'minimal',
            UserRole.CLIENT: 'none'
        }
        return levels.get(user_role, 'none')
    
    def create_system_alert(self, alert_type: str, message: str, severity: str = 'medium', 
                          metadata: Dict = None) -> bool:
        """시스템 알림 생성 (데이터베이스에 저장)"""
        try:
            RevenueAlert.objects.create(
                alert_type=alert_type,
                severity=severity,
                message=message,
                metadata=metadata or {},
                is_read=False,
                created_at=timezone.now()
            )
            
            logger.info(f"시스템 알림 생성: {alert_type} - {message}")
            return True
            
        except Exception as e:
            logger.error(f"시스템 알림 생성 실패: {e}")
            return False
    
    def mark_alert_as_read(self, alert_id: str, user: User) -> bool:
        """알림 읽음 처리"""
        try:
            alert = RevenueAlert.objects.get(id=alert_id)
            alert.is_read = True
            alert.read_at = timezone.now()
            alert.read_by = user
            alert.save()
            
            return True
            
        except RevenueAlert.DoesNotExist:
            logger.warning(f"존재하지 않는 알림 ID: {alert_id}")
            return False
        except Exception as e:
            logger.error(f"알림 읽음 처리 실패: {e}")
            return False
    
    def get_dashboard_widgets(self, user: User) -> Dict:
        """대시보드용 위젯 데이터 생성"""
        user_alerts = self.get_user_specific_alerts(user)
        
        # 우선순위별 알림 집계
        priority_count = {'high': 0, 'medium': 0, 'low': 0, 'info': 0}
        urgent_alerts = []
        
        for alert_type, alert_list in user_alerts['alerts'].items():
            for alert in alert_list:
                severity = alert.get('severity', 'medium')
                priority_count[severity] += 1
                
                if severity == 'high':
                    urgent_alerts.append(alert)
        
        # 상위 3개 긴급 알림만 표시
        urgent_alerts.sort(key=lambda x: x.get('priority', 3))
        
        return {
            'priority_summary': priority_count,
            'urgent_alerts': urgent_alerts[:3],
            'total_alerts': sum(priority_count.values()),
            'last_updated': timezone.now().isoformat(),
            'permission_level': user_alerts['permission_level']
        }


# 알림 처리를 위한 헬퍼 함수들
def send_revenue_notification(user: User, alert_data: Dict):
    """매출 알림 발송 (이메일, PWA 푸시 등)"""
    # PWA 푸시 알림
    send_pwa_notification(user, alert_data)
    
    # 이메일 알림 (고위험도만)
    if alert_data.get('severity') == 'high':
        send_email_notification(user, alert_data)

def send_pwa_notification(user: User, alert_data: Dict):
    """PWA 푸시 알림 발송"""
    # Service Worker를 통한 푸시 알림
    # 실제 구현에서는 WebPush API 사용
    pass

def send_email_notification(user: User, alert_data: Dict):
    """이메일 알림 발송"""
    # Django 이메일 발송
    # 실제 구현에서는 Celery로 백그라운드 처리
    pass