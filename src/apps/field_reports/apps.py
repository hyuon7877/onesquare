from django.apps import AppConfig


class FieldReportsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.field_reports'
    verbose_name = 'OneSquare 현장 리포트 시스템'
    
    def ready(self):
        """앱 초기화 시 실행되는 코드"""
        pass