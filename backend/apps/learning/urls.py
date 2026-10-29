from django.urls import path
from . import views

urlpatterns = [
    path('', views.learning_topics, name='learning_topics'),
]
