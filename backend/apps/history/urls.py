from django.urls import path
from . import views

urlpatterns = [
    path('', views.history_list, name='history_list'),
    path('sessions/<int:session_id>/', views.session_detail, name='session_detail'),
]
