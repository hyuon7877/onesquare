"""
OneSquare Dashboard 위젯 초기 설정 명령어
6개 사용자 그룹별 맞춤형 위젯 설정
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.dashboard.models import DashboardWidget


class Command(BaseCommand):
    help = '6개 사용자 그룹별 맞춤형 대시보드 위젯 초기 설정'
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Dashboard 위젯 설정을 시작합니다...')
        )
        
        try:
            with transaction.atomic():
                self.create_default_widgets()
            
            self.stdout.write(
                self.style.SUCCESS('✅ Dashboard 위젯 설정이 완료되었습니다!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 설정 중 오류가 발생했습니다: {str(e)}')
            )
    
    def create_default_widgets(self):
        """기본 위젯들 생성"""
        
        widgets_config = [
            # === 매출 관련 위젯 (관리자/매니저 전용) ===
            {
                'name': 'revenue_overview',
                'title': '매출 현황 개요',
                'description': '월별 매출 현황 및 목표 달성률',
                'widget_type': 'stats_card',
                'data_source': 'revenue',
                'accessible_user_types': ['SUPER_ADMIN', 'MANAGER'],
                'config': {
                    'icon': 'chart-line',
                    'color': '#28a745',
                    'show_trend': True,
                    'format': 'currency'
                },
                'default_width': 4,
                'default_height': 200
            },
            {
                'name': 'revenue_monthly_chart',
                'title': '월별 매출 추이',
                'description': '최근 12개월 매출 트렌드 차트',
                'widget_type': 'chart_line',
                'data_source': 'revenue',
                'accessible_user_types': ['SUPER_ADMIN', 'MANAGER'],
                'config': {
                    'icon': 'chart-line',
                    'time_range': '12m',
                    'show_points': True,
                    'smooth': True
                },
                'default_width': 8,
                'default_height': 300
            },
            {
                'name': 'revenue_by_category',
                'title': '카테고리별 매출',
                'description': '매출 카테고리 분포 원형 차트',
                'widget_type': 'chart_pie',
                'data_source': 'revenue',
                'accessible_user_types': ['SUPER_ADMIN', 'MANAGER'],
                'config': {
                    'icon': 'chart-pie',
                    'show_legend': True,
                    'show_labels': True
                },
                'default_width': 6,
                'default_height': 350
            },
            {
                'name': 'outstanding_payments',
                'title': '미수금 현황',
                'description': '미수금 및 연체 현황',
                'widget_type': 'stats_card',
                'data_source': 'revenue',
                'accessible_user_types': ['SUPER_ADMIN', 'MANAGER'],
                'config': {
                    'icon': 'exclamation-triangle',
                    'color': '#dc3545',
                    'format': 'currency',
                    'alert_threshold': 1000000
                },
                'default_width': 4,
                'default_height': 200
            },
            
            # === 캘린더 관련 위젯 (모든 사용자) ===
            {
                'name': 'upcoming_events',
                'title': '다가오는 일정',
                'description': '향후 7일간의 일정 목록',
                'widget_type': 'table',
                'data_source': 'calendar',
                'accessible_user_types': [],  # 모든 사용자 접근 가능
                'config': {
                    'icon': 'calendar-alt',
                    'time_range': '7d',
                    'max_items': 10
                },
                'default_width': 6,
                'default_height': 400
            },
            {
                'name': 'calendar_mini',
                'title': '미니 캘린더',
                'description': '이번 달 캘린더 위젯',
                'widget_type': 'calendar',
                'data_source': 'calendar',
                'accessible_user_types': [],  # 모든 사용자 접근 가능
                'config': {
                    'icon': 'calendar',
                    'view': 'month',
                    'compact': True
                },
                'default_width': 6,
                'default_height': 400
            },
            {
                'name': 'today_events',
                'title': '오늘의 일정',
                'description': '오늘 예정된 일정들',
                'widget_type': 'stats_card',
                'data_source': 'calendar',
                'accessible_user_types': [],  # 모든 사용자 접근 가능
                'config': {
                    'icon': 'clock',
                    'color': '#3788d8',
                    'format': 'count'
                },
                'default_width': 3,
                'default_height': 150
            },
            
            # === 프로젝트 관리 위젯 (관리자/매니저/팀원) ===
            {
                'name': 'active_projects',
                'title': '진행 중인 프로젝트',
                'description': '현재 진행 중인 프로젝트 현황',
                'widget_type': 'table',
                'data_source': 'revenue',
                'accessible_user_types': ['SUPER_ADMIN', 'MANAGER', 'TEAM_MEMBER'],
                'config': {
                    'icon': 'project-diagram',
                    'show_progress': True,
                    'max_items': 8
                },
                'default_width': 8,
                'default_height': 350
            },
            {
                'name': 'project_completion',
                'title': '프로젝트 완료율',
                'description': '프로젝트별 진행률 현황',
                'widget_type': 'progress',
                'data_source': 'revenue',
                'accessible_user_types': ['SUPER_ADMIN', 'MANAGER', 'TEAM_MEMBER'],
                'config': {
                    'icon': 'tasks',
                    'color': '#17a2b8',
                    'show_percentage': True
                },
                'default_width': 4,
                'default_height': 200
            },
            
            # === 파트너 리포트 위젯 (관리자/매니저) ===
            {
                'name': 'partner_reports',
                'title': '파트너 리포트 현황',
                'description': '최근 파트너 현장 리포트',
                'widget_type': 'table',
                'data_source': 'partner_report',
                'accessible_user_types': ['SUPER_ADMIN', 'MANAGER'],
                'config': {
                    'icon': 'clipboard-list',
                    'time_range': '7d',
                    'max_items': 10
                },
                'default_width': 6,
                'default_height': 400
            },
            {
                'name': 'field_activities',
                'title': '현장 활동 현황',
                'description': '오늘의 현장 활동 통계',
                'widget_type': 'stats_card',
                'data_source': 'partner_report',
                'accessible_user_types': ['SUPER_ADMIN', 'MANAGER'],
                'config': {
                    'icon': 'hard-hat',
                    'color': '#fd7e14',
                    'format': 'count'
                },
                'default_width': 4,
                'default_height': 200
            },
            
            # === 시스템 상태 위젯 (최고관리자 전용) ===
            {
                'name': 'system_health',
                'title': '시스템 상태',
                'description': '서버 및 시스템 상태 모니터링',
                'widget_type': 'stats_card',
                'data_source': 'system_status',
                'accessible_user_types': ['SUPER_ADMIN'],
                'config': {
                    'icon': 'server',
                    'color': '#6f42c1',
                    'show_status': True
                },
                'default_width': 4,
                'default_height': 200
            },
            {
                'name': 'notion_sync_status',
                'title': 'Notion 동기화 상태',
                'description': 'Notion API 연동 상태',
                'widget_type': 'stats_card',
                'data_source': 'notion_sync',
                'accessible_user_types': ['SUPER_ADMIN', 'MANAGER'],
                'config': {
                    'icon': 'sync-alt',
                    'color': '#20c997',
                    'show_last_sync': True
                },
                'default_width': 4,
                'default_height': 200
            },
            
            # === 사용자 활동 위젯 ===
            {
                'name': 'user_activity',
                'title': '사용자 활동',
                'description': '최근 사용자 활동 현황',
                'widget_type': 'table',
                'data_source': 'user_activity',
                'accessible_user_types': ['SUPER_ADMIN', 'MANAGER'],
                'config': {
                    'icon': 'users',
                    'time_range': '24h',
                    'max_items': 8
                },
                'default_width': 6,
                'default_height': 350
            },
            
            # === 알림 위젯 (모든 사용자) ===
            {
                'name': 'notifications_panel',
                'title': '최근 알림',
                'description': '최근 알림 및 공지사항',
                'widget_type': 'notification',
                'data_source': 'notification',
                'accessible_user_types': [],  # 모든 사용자 접근 가능
                'config': {
                    'icon': 'bell',
                    'max_items': 5,
                    'show_unread_only': False
                },
                'default_width': 6,
                'default_height': 300
            },
            
            # === 개인 대시보드 위젯 (팀원/파트너/도급사용) ===
            {
                'name': 'my_tasks',
                'title': '내 업무',
                'description': '개인 할당 업무 현황',
                'widget_type': 'table',
                'data_source': 'user_activity',
                'accessible_user_types': ['TEAM_MEMBER', 'PARTNER', 'CONTRACTOR'],
                'config': {
                    'icon': 'clipboard-check',
                    'personal_only': True,
                    'max_items': 8
                },
                'default_width': 8,
                'default_height': 350
            },
            {
                'name': 'my_schedule',
                'title': '내 일정',
                'description': '개인 일정 요약',
                'widget_type': 'stats_card',
                'data_source': 'calendar',
                'accessible_user_types': ['TEAM_MEMBER', 'PARTNER', 'CONTRACTOR'],
                'config': {
                    'icon': 'user-clock',
                    'color': '#6c757d',
                    'personal_only': True,
                    'format': 'count'
                },
                'default_width': 4,
                'default_height': 200
            }
        ]
        
        # 위젯 생성
        created_count = 0
        for widget_config in widgets_config:
            widget, created = DashboardWidget.objects.get_or_create(
                name=widget_config['name'],
                defaults=widget_config
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'  ✓ Created widget: {widget.title}')
            else:
                # 기존 위젯 업데이트
                for key, value in widget_config.items():
                    if key != 'name':
                        setattr(widget, key, value)
                widget.save()
                self.stdout.write(f'  ↻ Updated widget: {widget.title}')
        
        self.stdout.write(
            self.style.SUCCESS(f'📊 총 {len(widgets_config)}개 위젯 중 {created_count}개 신규 생성')
        )