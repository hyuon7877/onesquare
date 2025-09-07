"""Revenue 권한 모듈

수익 관련 모든 권한 클래스 통합
"""

from .base import (
    IsOwnerOrReadOnly,
    IsManagerOrAbove,
    IsSupervisorOrAbove,
    HasDepartmentAccess
)

from .revenue_permissions import (
    CanViewRevenue,
    CanEditRevenue,
    CanDeleteRevenue,
    CanApproveRevenue
)

from .report_permissions import (
    CanViewReport,
    CanGenerateReport,
    CanExportReport,
    CanShareReport
)

from .budget_permissions import (
    CanViewBudget,
    CanEditBudget,
    CanApproveBudget,
    CanAllocateBudget
)

from .analytics_permissions import (
    CanViewAnalytics,
    CanAccessAdvancedAnalytics,
    CanExportAnalytics,
    CanViewDashboard
)

__all__ = [
    # Base permissions
    'IsOwnerOrReadOnly',
    'IsManagerOrAbove',
    'IsSupervisorOrAbove',
    'HasDepartmentAccess',
    
    # Revenue permissions
    'CanViewRevenue',
    'CanEditRevenue',
    'CanDeleteRevenue',
    'CanApproveRevenue',
    
    # Report permissions
    'CanViewReport',
    'CanGenerateReport',
    'CanExportReport',
    'CanShareReport',
    
    # Budget permissions
    'CanViewBudget',
    'CanEditBudget',
    'CanApproveBudget',
    'CanAllocateBudget',
    
    # Analytics permissions
    'CanViewAnalytics',
    'CanAccessAdvancedAnalytics',
    'CanExportAnalytics',
    'CanViewDashboard',
]
