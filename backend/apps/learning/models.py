"""
Learning models for BugSense AI.
"""

from django.db import models
from django.conf import settings
from django.db.models import UniqueConstraint


class LearningTopic(models.Model):
    """Educational learning topic."""

    CATEGORY_CHOICES = [
        ('fundamentals', 'Error Fundamentals'), ('traces', 'Traceback & Stack Trace Analysis'),
        ('databases', 'Database Troubleshooting'), ('api_http', 'API & HTTP Debugging'),
        ('django_backend', 'Django & Backend Errors'), ('frontend_js', 'Frontend & JavaScript Errors'),
        ('deployment', 'Deployment & Environment Errors'), ('verification', 'Debugging & Verification'),
    ]

    title = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    description = models.TextField()
    explanation = models.TextField()
    buggy_code = models.TextField()
    expected_error = models.TextField()
    corrected_code = models.TextField()
    correction_explanation = models.TextField()
    practice_question = models.TextField(blank=True)
    practice_answer = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    error_name = models.CharField(max_length=120, blank=True, default='')
    difficulty = models.CharField(max_length=16, choices=[('beginner','Beginner'),('intermediate','Intermediate'),('advanced','Advanced')], default='beginner')
    technology = models.CharField(max_length=80, blank=True, default='')
    keywords = models.JSONField(default=list, blank=True)
    lesson_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'learning_topics'
        ordering = ['order', 'category']

    def __str__(self):
        return self.title


class LearningActivity(models.Model):
    """User-specific practice generated from an actual analysis or log explanation."""
    ACTIVITY_CHOICES = [('practice', 'Practice'), ('quiz', 'Understanding Check'), ('lesson', 'Lesson')]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='learning_activities')
    session = models.ForeignKey('dashboard.DebuggingSession', on_delete=models.SET_NULL, null=True, blank=True, related_name='learning_activities')
    activity_type = models.CharField(max_length=16, choices=ACTIVITY_CHOICES)
    prompt = models.TextField()
    answer = models.TextField(blank=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'learning_activities'
        ordering = ['-created_at']


class LearningProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='debugging_lesson_progress')
    topic = models.ForeignKey(LearningTopic, on_delete=models.CASCADE, related_name='user_progress')
    completed = models.BooleanField(default=False)
    bookmarked = models.BooleanField(default=False)
    last_studied = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [UniqueConstraint(fields=['user','topic'], name='learning_progress_user_topic_unique')]


class ExerciseSubmission(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='debugging_exercise_submissions')
    topic = models.ForeignKey(LearningTopic, on_delete=models.CASCADE, related_name='exercise_submissions')
    difficulty = models.CharField(max_length=16, choices=[('beginner','Beginner'),('intermediate','Intermediate'),('advanced','Advanced')])
    proposed_line = models.TextField(blank=True)
    root_cause = models.TextField()
    proposed_fix = models.TextField()
    hints_revealed = models.PositiveSmallIntegerField(default=0)
    solved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']


class QuizAttempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='debugging_quiz_attempts')
    topic = models.ForeignKey(LearningTopic, on_delete=models.CASCADE, related_name='quiz_attempts')
    score = models.PositiveSmallIntegerField()
    total = models.PositiveSmallIntegerField()
    responses = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
