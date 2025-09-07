"""Time Tracking Views 모듈

시간 추적 관련 모든 뷰 통합
"""

from .calendar_views import (
    calendar_view,
    calendar_api,
    add_calendar_event
)

from .timesheet_views import (
    timesheet_list,
    timesheet_detail,
    timesheet_create,
    timesheet_submit,
    timesheet_approve
)

from .report_views import (
    time_report_dashboard,
    productivity_report,
    team_time_report,
    export_time_report
)

from .entry_views import (
    time_entry_form,
    time_entry_list,
    time_entry_edit,
    time_entry_delete,
    quick_time_entry
)

__all__ = [
    # Calendar
    'calendar_view',
    'calendar_api',
    'add_calendar_event',
    
    # Timesheet
    'timesheet_list',
    'timesheet_detail',
    'timesheet_create',
    'timesheet_submit',
    'timesheet_approve',
    
    # Reports
    'time_report_dashboard',
    'productivity_report',
    'team_time_report',
    'export_time_report',
    
    # Entries
    'time_entry_form',
    'time_entry_list',
    'time_entry_edit',
    'time_entry_delete',
    'quick_time_entry',
]
