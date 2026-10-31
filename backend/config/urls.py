"""
URL configuration for BugSense AI project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse


def api_info(request):
    """API info endpoint at root."""
    return JsonResponse({
        'name': 'BugSense AI API',
        'version': '1.0.0',
        'description': 'AI-powered autonomous debugging platform',
        'endpoints': {
            'auth': '/api/v1/auth/',
            'dashboard': '/api/v1/dashboard/',
            'projects': '/api/v1/projects/',
            'analysis': '/api/v1/analysis/',
            'repair': '/api/v1/repair/',
            'execution': '/api/v1/execution/',
            'verification': '/api/v1/verification/',
            'history': '/api/v1/history/',
            'learning': '/api/v1/learning/',
        },
        'frontend': 'http://127.0.0.1:5173',
        'documentation': 'Visit /api/v1/ for available endpoints'
    })


urlpatterns = [
    path('', api_info, name='api_info'),
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/dashboard/', include('apps.dashboard.urls')),
    path('api/v1/projects/', include('apps.projects.urls')),
    path('api/v1/analysis/', include('apps.analysis.urls')),
    path('api/v1/repair/', include('apps.repair.urls')),
    path('api/v1/execution/', include('apps.execution.urls')),
    path('api/v1/verification/', include('apps.verification.urls')),
    path('api/v1/history/', include('apps.history.urls')),
    path('api/v1/learning/', include('apps.learning.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
