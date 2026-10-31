from django.urls import path
from . import views
from .logsense_views import explain_log

urlpatterns = [
    path('health/', views.ai_provider_health, name='ai_provider_health'),
    path('analyze/', views.create_analysis, name='create_analysis'),
    path('logsense/', explain_log, name='logsense_explain'),
]
