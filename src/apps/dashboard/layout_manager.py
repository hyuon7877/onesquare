"""
OneSquare 대시보드 레이아웃 관리자
6개 사용자 그룹별 맞춤형 레이아웃 및 개인화 기능
"""

from django.db.models import Q
from django.contrib.auth import get_user_model
from .models import DashboardWidget, UserDashboard, UserWidgetSettings
import json

User = get_user_model()


class DashboardLayoutManager:
    """대시보드 레이아웃 관리 클래스"""
    
    def __init__(self, user):
        self.user = user
        self.user_type = user.user_type
    
    def get_default_layout_for_user_type(self, user_type):
        """사용자 타입별 기본 레이아웃 정의"""
        
        layouts = {
            # 최고관리자 - 전체 시스템 관리 중심
            'SUPER_ADMIN': {
                'layout_type': 'grid',
                'theme': 'light',
                'primary_color': '#dc3545',  # 빨간색 - 관리자 테마
                'widgets': [
                    {'name': 'system_health', 'x': 0, 'y': 0, 'width': 3, 'height': 200, 'order': 1},
                    {'name': 'notion_sync_status', 'x': 3, 'y': 0, 'width': 3, 'height': 200, 'order': 2},
                    {'name': 'revenue_overview', 'x': 6, 'y': 0, 'width': 3, 'height': 200, 'order': 3},
                    {'name': 'outstanding_payments', 'x': 9, 'y': 0, 'width': 3, 'height': 200, 'order': 4},
                    
                    {'name': 'revenue_monthly_chart', 'x': 0, 'y': 1, 'width': 8, 'height': 300, 'order': 5},
                    {'name': 'revenue_by_category', 'x': 8, 'y': 1, 'width': 4, 'height': 300, 'order': 6},
                    
                    {'name': 'user_activity', 'x': 0, 'y': 2, 'width': 6, 'height': 350, 'order': 7},
                    {'name': 'partner_reports', 'x': 6, 'y': 2, 'width': 6, 'height': 350, 'order': 8},
                    
                    {'name': 'active_projects', 'x': 0, 'y': 3, 'width': 8, 'height': 350, 'order': 9},
                    {'name': 'notifications_panel', 'x': 8, 'y': 3, 'width': 4, 'height': 350, 'order': 10},
                ]
            },
            
            # 중간관리자 - 매출 및 프로젝트 관리 중심
            'MANAGER': {
                'layout_type': 'grid',
                'theme': 'light',
                'primary_color': '#28a745',  # 녹색 - 매니저 테마
                'widgets': [
                    {'name': 'revenue_overview', 'x': 0, 'y': 0, 'width': 4, 'height': 200, 'order': 1},
                    {'name': 'project_completion', 'x': 4, 'y': 0, 'width': 4, 'height': 200, 'order': 2},
                    {'name': 'today_events', 'x': 8, 'y': 0, 'width': 4, 'height': 200, 'order': 3},
                    
                    {'name': 'revenue_monthly_chart', 'x': 0, 'y': 1, 'width': 8, 'height': 300, 'order': 4},
                    {'name': 'upcoming_events', 'x': 8, 'y': 1, 'width': 4, 'height': 300, 'order': 5},
                    
                    {'name': 'active_projects', 'x': 0, 'y': 2, 'width': 8, 'height': 350, 'order': 6},
                    {'name': 'partner_reports', 'x': 8, 'y': 2, 'width': 4, 'height': 350, 'order': 7},
                    
                    {'name': 'revenue_by_category', 'x': 0, 'y': 3, 'width': 6, 'height': 350, 'order': 8},
                    {'name': 'notifications_panel', 'x': 6, 'y': 3, 'width': 6, 'height': 350, 'order': 9},
                ]
            },
            
            # 팀원 - 개인 업무 및 프로젝트 중심
            'TEAM_MEMBER': {
                'layout_type': 'grid',
                'theme': 'light',
                'primary_color': '#3788d8',  # 파란색 - 기본 테마
                'widgets': [
                    {'name': 'my_schedule', 'x': 0, 'y': 0, 'width': 4, 'height': 200, 'order': 1},
                    {'name': 'today_events', 'x': 4, 'y': 0, 'width': 4, 'height': 200, 'order': 2},
                    {'name': 'project_completion', 'x': 8, 'y': 0, 'width': 4, 'height': 200, 'order': 3},
                    
                    {'name': 'my_tasks', 'x': 0, 'y': 1, 'width': 8, 'height': 350, 'order': 4},
                    {'name': 'upcoming_events', 'x': 8, 'y': 1, 'width': 4, 'height': 350, 'order': 5},
                    
                    {'name': 'calendar_mini', 'x': 0, 'y': 2, 'width': 6, 'height': 400, 'order': 6},
                    {'name': 'notifications_panel', 'x': 6, 'y': 2, 'width': 6, 'height': 400, 'order': 7},
                ]
            },
            
            # 파트너 - 개인 업무 및 현장 리포트 중심
            'PARTNER': {
                'layout_type': 'grid',
                'theme': 'light',
                'primary_color': '#fd7e14',  # 주황색 - 파트너 테마
                'widgets': [
                    {'name': 'my_schedule', 'x': 0, 'y': 0, 'width': 6, 'height': 200, 'order': 1},
                    {'name': 'today_events', 'x': 6, 'y': 0, 'width': 6, 'height': 200, 'order': 2},
                    
                    {'name': 'my_tasks', 'x': 0, 'y': 1, 'width': 8, 'height': 350, 'order': 3},
                    {'name': 'calendar_mini', 'x': 8, 'y': 1, 'width': 4, 'height': 350, 'order': 4},
                    
                    {'name': 'upcoming_events', 'x': 0, 'y': 2, 'width': 8, 'height': 400, 'order': 5},
                    {'name': 'notifications_panel', 'x': 8, 'y': 2, 'width': 4, 'height': 400, 'order': 6},
                ]
            },
            
            # 도급사 - 개인 업무 중심 (파트너와 유사하지만 더 단순)
            'CONTRACTOR': {
                'layout_type': 'grid',
                'theme': 'light',
                'primary_color': '#6f42c1',  # 보라색 - 도급사 테마
                'widgets': [
                    {'name': 'my_schedule', 'x': 0, 'y': 0, 'width': 6, 'height': 200, 'order': 1},
                    {'name': 'today_events', 'x': 6, 'y': 0, 'width': 6, 'height': 200, 'order': 2},
                    
                    {'name': 'my_tasks', 'x': 0, 'y': 1, 'width': 12, 'height': 350, 'order': 3},
                    
                    {'name': 'calendar_mini', 'x': 0, 'y': 2, 'width': 6, 'height': 400, 'order': 4},
                    {'name': 'notifications_panel', 'x': 6, 'y': 2, 'width': 6, 'height': 400, 'order': 5},
                ]
            },
            
            # 커스텀 - 기본 레이아웃 (팀원과 동일)
            'CUSTOM': {
                'layout_type': 'grid',
                'theme': 'light',
                'primary_color': '#6c757d',  # 회색 - 커스텀 테마
                'widgets': [
                    {'name': 'today_events', 'x': 0, 'y': 0, 'width': 4, 'height': 200, 'order': 1},
                    {'name': 'my_schedule', 'x': 4, 'y': 0, 'width': 4, 'height': 200, 'order': 2},
                    {'name': 'notifications_panel', 'x': 8, 'y': 0, 'width': 4, 'height': 200, 'order': 3},
                    
                    {'name': 'calendar_mini', 'x': 0, 'y': 1, 'width': 6, 'height': 400, 'order': 4},
                    {'name': 'upcoming_events', 'x': 6, 'y': 1, 'width': 6, 'height': 400, 'order': 5},
                ]
            }
        }
        
        return layouts.get(user_type, layouts['CUSTOM'])
    
    def setup_user_dashboard(self, force_reset=False):
        """사용자 대시보드 초기 설정"""
        
        # 기존 대시보드 설정 확인
        user_dashboard, created = UserDashboard.objects.get_or_create(
            user=self.user,
            defaults={
                'layout_type': 'grid',
                'theme': 'light',
                'primary_color': '#3788d8',
            }
        )
        
        # 기본 레이아웃 가져오기
        default_layout = self.get_default_layout_for_user_type(self.user_type)
        
        # 대시보드 기본 설정 업데이트 (새 사용자이거나 강제 리셋인 경우)
        if created or force_reset:
            user_dashboard.layout_type = default_layout['layout_type']
            user_dashboard.theme = default_layout['theme']
            user_dashboard.primary_color = default_layout['primary_color']
            user_dashboard.save()
        
        # 기존 위젯 설정 확인
        existing_widgets = UserWidgetSettings.objects.filter(
            dashboard=user_dashboard
        ).count()
        
        # 위젯이 없거나 강제 리셋인 경우 기본 위젯 설정
        if existing_widgets == 0 or force_reset:
            if force_reset:
                UserWidgetSettings.objects.filter(dashboard=user_dashboard).delete()
            
            self._setup_default_widgets(user_dashboard, default_layout['widgets'])
        
        return user_dashboard
    
    def _setup_default_widgets(self, user_dashboard, widget_configs):
        """기본 위젯들 설정"""
        
        for widget_config in widget_configs:
            try:
                # 위젯 찾기
                widget = DashboardWidget.objects.get(name=widget_config['name'])
                
                # 접근 권한 확인
                if not widget.can_access(self.user):
                    continue
                
                # 위젯 설정 생성
                UserWidgetSettings.objects.create(
                    dashboard=user_dashboard,
                    widget=widget,
                    position_x=widget_config['x'],
                    position_y=widget_config['y'],
                    width=widget_config['width'],
                    height=widget_config['height'],
                    order=widget_config['order'],
                    is_visible=True
                )
                
            except DashboardWidget.DoesNotExist:
                # 위젯이 존재하지 않으면 건너뛰기
                print(f"Warning: Widget '{widget_config['name']}' not found")
                continue
    
    def get_available_widgets(self):
        """사용자가 접근 가능한 위젯 목록 조회"""
        
        return DashboardWidget.objects.filter(
            is_active=True
        ).filter(
            Q(accessible_user_types__isnull=True) |
            Q(accessible_user_types__contains=[self.user_type])
        ).order_by('widget_type', 'title')
    
    def get_user_widgets(self):
        """사용자의 현재 위젯 설정 조회"""
        
        user_dashboard = UserDashboard.objects.filter(user=self.user).first()
        if not user_dashboard:
            user_dashboard = self.setup_user_dashboard()
        
        return UserWidgetSettings.objects.filter(
            dashboard=user_dashboard,
            is_visible=True
        ).select_related('widget').order_by('order')
    
    def add_widget_to_dashboard(self, widget_id, position=None):
        """대시보드에 위젯 추가"""
        
        try:
            widget = DashboardWidget.objects.get(id=widget_id)
            
            # 접근 권한 확인
            if not widget.can_access(self.user):
                return False, "접근 권한이 없습니다."
            
            # 사용자 대시보드 가져오기
            user_dashboard, _ = UserDashboard.objects.get_or_create(
                user=self.user
            )
            
            # 이미 추가된 위젯인지 확인
            if UserWidgetSettings.objects.filter(
                dashboard=user_dashboard,
                widget=widget
            ).exists():
                return False, "이미 추가된 위젯입니다."
            
            # 위치 설정 (제공되지 않으면 자동 계산)
            if not position:
                position = self._calculate_next_position(user_dashboard)
            
            # 위젯 설정 생성
            UserWidgetSettings.objects.create(
                dashboard=user_dashboard,
                widget=widget,
                position_x=position.get('x', 0),
                position_y=position.get('y', 0),
                width=position.get('width', widget.default_width),
                height=position.get('height', widget.default_height),
                order=position.get('order', self._get_next_order(user_dashboard)),
                is_visible=True
            )
            
            return True, f"{widget.title} 위젯이 추가되었습니다."
            
        except DashboardWidget.DoesNotExist:
            return False, "위젯을 찾을 수 없습니다."
        except Exception as e:
            return False, f"위젯 추가 중 오류가 발생했습니다: {str(e)}"
    
    def remove_widget_from_dashboard(self, widget_id):
        """대시보드에서 위젯 제거"""
        
        try:
            user_dashboard = UserDashboard.objects.get(user=self.user)
            widget_setting = UserWidgetSettings.objects.get(
                dashboard=user_dashboard,
                widget_id=widget_id
            )
            
            widget_title = widget_setting.widget.title
            widget_setting.delete()
            
            return True, f"{widget_title} 위젯이 제거되었습니다."
            
        except (UserDashboard.DoesNotExist, UserWidgetSettings.DoesNotExist):
            return False, "위젯 설정을 찾을 수 없습니다."
        except Exception as e:
            return False, f"위젯 제거 중 오류가 발생했습니다: {str(e)}"
    
    def update_widget_layout(self, layouts):
        """위젯 레이아웃 업데이트 (드래그 앤 드롭용)"""
        
        try:
            user_dashboard = UserDashboard.objects.get(user=self.user)
            
            for layout in layouts:
                widget_setting = UserWidgetSettings.objects.get(
                    dashboard=user_dashboard,
                    widget_id=layout['widget_id']
                )
                
                widget_setting.position_x = layout.get('x', widget_setting.position_x)
                widget_setting.position_y = layout.get('y', widget_setting.position_y)
                widget_setting.width = layout.get('width', widget_setting.width)
                widget_setting.height = layout.get('height', widget_setting.height)
                widget_setting.order = layout.get('order', widget_setting.order)
                widget_setting.save()
            
            return True, "레이아웃이 저장되었습니다."
            
        except Exception as e:
            return False, f"레이아웃 저장 중 오류가 발생했습니다: {str(e)}"
    
    def reset_to_default_layout(self):
        """기본 레이아웃으로 리셋"""
        return self.setup_user_dashboard(force_reset=True)
    
    def _calculate_next_position(self, user_dashboard):
        """다음 위젯 위치 자동 계산"""
        
        existing_widgets = UserWidgetSettings.objects.filter(
            dashboard=user_dashboard,
            is_visible=True
        ).order_by('-position_y', '-position_x')
        
        if not existing_widgets.exists():
            return {'x': 0, 'y': 0, 'width': 4, 'height': 300}
        
        # 가장 아래쪽 위젯 찾기
        last_widget = existing_widgets.first()
        
        # 새 위젯을 다음 행에 배치
        return {
            'x': 0,
            'y': last_widget.position_y + 1,
            'width': 4,
            'height': 300
        }
    
    def _get_next_order(self, user_dashboard):
        """다음 위젯 순서 번호 계산"""
        
        last_order = UserWidgetSettings.objects.filter(
            dashboard=user_dashboard
        ).aggregate(
            models.Max('order')
        )['order__max']
        
        return (last_order or 0) + 1
    
    def export_layout(self):
        """현재 레이아웃 내보내기 (JSON 형태)"""
        
        try:
            user_dashboard = UserDashboard.objects.get(user=self.user)
            user_widgets = UserWidgetSettings.objects.filter(
                dashboard=user_dashboard
            ).select_related('widget').order_by('order')
            
            layout_data = {
                'user_type': self.user_type,
                'layout_type': user_dashboard.layout_type,
                'theme': user_dashboard.theme,
                'primary_color': user_dashboard.primary_color,
                'widgets': []
            }
            
            for widget_setting in user_widgets:
                layout_data['widgets'].append({
                    'name': widget_setting.widget.name,
                    'title': widget_setting.custom_title or widget_setting.widget.title,
                    'x': widget_setting.position_x,
                    'y': widget_setting.position_y,
                    'width': widget_setting.width,
                    'height': widget_setting.height,
                    'order': widget_setting.order,
                    'is_visible': widget_setting.is_visible,
                    'custom_config': widget_setting.custom_config
                })
            
            return layout_data
            
        except UserDashboard.DoesNotExist:
            return None
    
    def import_layout(self, layout_data):
        """레이아웃 가져오기"""
        
        try:
            # 기존 설정 제거
            user_dashboard = self.setup_user_dashboard(force_reset=True)
            
            # 대시보드 기본 설정 적용
            if 'layout_type' in layout_data:
                user_dashboard.layout_type = layout_data['layout_type']
            if 'theme' in layout_data:
                user_dashboard.theme = layout_data['theme']
            if 'primary_color' in layout_data:
                user_dashboard.primary_color = layout_data['primary_color']
            user_dashboard.save()
            
            # 위젯 설정 적용
            for widget_config in layout_data.get('widgets', []):
                try:
                    widget = DashboardWidget.objects.get(name=widget_config['name'])
                    
                    if widget.can_access(self.user):
                        UserWidgetSettings.objects.create(
                            dashboard=user_dashboard,
                            widget=widget,
                            custom_title=widget_config.get('title', ''),
                            position_x=widget_config.get('x', 0),
                            position_y=widget_config.get('y', 0),
                            width=widget_config.get('width', widget.default_width),
                            height=widget_config.get('height', widget.default_height),
                            order=widget_config.get('order', 0),
                            is_visible=widget_config.get('is_visible', True),
                            custom_config=widget_config.get('custom_config', {})
                        )
                        
                except DashboardWidget.DoesNotExist:
                    continue
            
            return True, "레이아웃을 성공적으로 가져왔습니다."
            
        except Exception as e:
            return False, f"레이아웃 가져오기 중 오류가 발생했습니다: {str(e)}"


def get_layout_manager(user):
    """레이아웃 매니저 팩토리 함수"""
    return DashboardLayoutManager(user)