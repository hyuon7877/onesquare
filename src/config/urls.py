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
    
    # Home page - redirect to dashboard
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    
    # Authentication System
    path('accounts/', include('accounts.urls')),
    
    # Calendar System (최상위 레벨로 이동)
    path('calendar/', include('dashboard.urls_calendar')),
    
    # Dashboard System
    path('dashboard/', include('dashboard.urls')),
    
    # Field Reports System
    path('field-reports/', include('field_reports.urls')),
    
    # Collaboration System
    path('collaboration/', include('collaboration.urls')),
    
    # Search System
    path('search/', include('search.urls')),
    
    # PWA Offline page
    path('offline/', TemplateView.as_view(template_name='offline.html'), name='offline'),
]

# Static and media files serving in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)