"""
URL configuration for onesquare project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # PWA URLs
    path('', include('apps.pwa.urls')),
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    
    # Revenue Management System
    path('revenue/', include('apps.revenue.urls')),
    
    # API URLs
    path('api/notion/', include('apps.notion_api.urls')),
    path('api/auth/', include('apps.auth_system.urls')),
    path('calendar/', include('apps.calendar_system.urls')),
    path('api/reports/', include('apps.field_reports.urls')),
    
    # Dashboard System
    path('dashboard/', include('apps.dashboard.urls')),
    
    # Leave Management System
    path('leave/', include('apps.leave_management.urls')),
    
    # Time Management System
    path('time/', include('apps.time_management.urls')),
    
    # Multimedia Feedback System
    path('feedback/', include('apps.feedback.urls')),
    
    # AI Analytics System
    path('ai-analytics/', include('apps.ai_analytics.urls')),
    
    # System Monitoring Dashboard
    path('monitoring/', include('apps.monitoring.urls')),
]

# Static and media files serving in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)