from django.apps import AppConfig


class RevenueConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.revenue'
    verbose_name = 'Revenue Management'
    
    def ready(self):
        """앱이 준비되었을 때 실행되는 코드"""
        try:
            # 시그널 등록 (필요한 경우)
            import apps.revenue.signals
        except ImportError:
            pass
