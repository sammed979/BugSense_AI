from django.urls import path
from . import views

urlpatterns = [
    path('', views.project_list, name='project_list'),
    path('upload/', views.upload_project, name='upload_project'),
    path('upload/single/', views.upload_single_file, name='upload_single_file'),
    path('upload/multiple/', views.upload_multiple_files, name='upload_multiple_files'),
    path('<int:project_id>/files/', views.project_files, name='project_files'),
    path('<int:project_id>/analysis/', views.project_analysis, name='project_analysis'),
    path('<int:project_id>/issues/', views.project_issues, name='project_issues'),
    path('<int:project_id>/analyze/', views.analyze_project, name='analyze_project'),
    path('<int:project_id>/analyze-static/', views.run_static_analysis, name='run_static_analysis'),
    path('<int:project_id>/analyze-ai/', views.run_ai_analysis, name='run_ai_analysis'),
    path('<int:project_id>/repair/generate/', views.generate_repair, name='generate_repair'),
    path('<int:project_id>/repair/apply/', views.apply_repair, name='apply_repair'),
    path('<int:project_id>/repair/reject/', views.reject_repair, name='reject_repair'),
    path('<int:project_id>/repair/rollback/', views.rollback_change, name='rollback_change'),
    path('<int:project_id>/download/', views.download_project, name='download_project'),
    path('<int:project_id>/', views.project_detail, name='project_detail'),
]
