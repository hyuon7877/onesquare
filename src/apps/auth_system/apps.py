from django.apps import AppConfig


class AuthSystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.auth_system'
    verbose_name = '사용자 인증 시스템'
    
    def ready(self):
        """앱이 준비될 때 실행되는 메서드"""
        import apps.auth_system.signals