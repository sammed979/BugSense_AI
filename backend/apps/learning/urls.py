from django.urls import path
from . import views

urlpatterns = [
    path('', views.learning_topics, name='learning_topics'),
    path('dashboard/', views.learning_dashboard, name='learning_dashboard'),
    path('recommendations/', views.learning_recommendations, name='learning_recommendations'),
    path('lessons/<int:topic_id>/', views.lesson_progress, name='learning_lesson'),
    path('lessons/<int:topic_id>/exercise/', views.submit_exercise, name='learning_exercise'),
    path('lessons/<int:topic_id>/quiz/', views.submit_quiz, name='learning_quiz'),
    path('activities/', views.learning_activities, name='learning_activities'),
]
