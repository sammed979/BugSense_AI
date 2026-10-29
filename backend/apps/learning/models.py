"""
Learning models for BugSense AI.
"""

from django.db import models


class LearningTopic(models.Model):
    """Educational learning topic."""

    CATEGORY_CHOICES = [
        ('errors', 'Python Errors'),
        ('debugging', 'Debugging Techniques'),
        ('testing', 'Testing'),
        ('static_analysis', 'Static Analysis'),
        ('safe_repair', 'Safe Code Repair'),
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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'learning_topics'
        ordering = ['order', 'category']

    def __str__(self):
        return self.title
