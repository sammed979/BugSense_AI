from django.urls import path
from . import views

urlpatterns = [
    path('', views.project_list, name='project_list'),
    path('upload/', views.upload_project, name='upload_project'),
    path('<int:project_id>/', views.project_detail, name='project_detail'),
]
