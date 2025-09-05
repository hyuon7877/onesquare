from django.apps import AppConfig


class NotionApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notion_api'
    verbose_name = 'Notion API Integration'