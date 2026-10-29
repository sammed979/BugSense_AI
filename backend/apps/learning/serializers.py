from rest_framework import serializers
from .models import LearningTopic


class LearningTopicSerializer(serializers.ModelSerializer):
    """Serializer for LearningTopic model."""

    class Meta:
        model = LearningTopic
        fields = [
            'id', 'title', 'category', 'description', 'explanation',
            'buggy_code', 'expected_error', 'corrected_code',
            'correction_explanation', 'practice_question', 'practice_answer'
        ]
        read_only_fields = ['id']
