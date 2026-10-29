from rest_framework import serializers
from .models import DebuggingSession, AnalysisResult


class DebuggingSessionSerializer(serializers.ModelSerializer):
    """Serializer for DebuggingSession model."""

    class Meta:
        model = DebuggingSession
        fields = [
            'id', 'title', 'error_message', 'terminal_logs',
            'source_code', 'language', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AnalysisResultSerializer(serializers.ModelSerializer):
    """Serializer for AnalysisResult model."""

    class Meta:
        model = AnalysisResult
        fields = [
            'id', 'root_cause_summary', 'evidence', 'affected_files',
            'proposed_solution', 'ai_provider', 'ai_model', 'confidence',
            'confidence_explanation', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
