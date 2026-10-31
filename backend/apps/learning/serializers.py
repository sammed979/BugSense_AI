from rest_framework import serializers
from .models import LearningTopic


class LearningTopicSerializer(serializers.ModelSerializer):
    """Serializer for LearningTopic model."""

    class Meta:
        model = LearningTopic
        fields = [
            'id', 'title', 'category', 'error_name', 'technology', 'difficulty',
            'description', 'explanation', 'buggy_code', 'expected_error', 'practice_question'
        ]
        read_only_fields = ['id']
