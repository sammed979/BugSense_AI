from rest_framework import serializers
from apps.dashboard.models import Project, ProjectFile, ProjectAnalysis, ProjectIssue, FileDependency, SuggestedFix, AppliedChange


class ProjectSerializer(serializers.ModelSerializer):
    """Serializer for Project model."""

    class Meta:
        model = Project
        fields = ['id', 'name', 'source_type', 'language', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProjectFileSerializer(serializers.ModelSerializer):
    """Serializer for ProjectFile model."""

    class Meta:
        model = ProjectFile
        fields = ['id', 'path', 'content', 'updated_at']
        read_only_fields = ['id', 'updated_at']


class ProjectAnalysisSerializer(serializers.ModelSerializer):
    """Serializer for ProjectAnalysis model."""

    class Meta:
        model = ProjectAnalysis
        fields = ['id', 'analysis_type', 'status', 'total_files', 'analyzed_files', 'summary', 
                  'started_at', 'completed_at', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProjectIssueSerializer(serializers.ModelSerializer):
    """Serializer for ProjectIssue model."""

    class Meta:
        model = ProjectIssue
        fields = ['id', 'issue_id', 'severity', 'category', 'affected_file', 'line_number',
                  'line_range_end', 'explanation', 'supporting_evidence', 'related_files',
                  'root_cause', 'suggested_solution', 'confidence', 'status', 'created_at']
        read_only_fields = ['id', 'created_at']


class FileDependencySerializer(serializers.ModelSerializer):
    """Serializer for FileDependency model."""

    class Meta:
        model = FileDependency
        fields = ['id', 'source_file', 'target_file', 'dependency_type', 'line_number', 'created_at']
        read_only_fields = ['id', 'created_at']


class SuggestedFixSerializer(serializers.ModelSerializer):
    """Serializer for SuggestedFix model."""

    class Meta:
        model = SuggestedFix
        fields = ['id', 'original_code', 'suggested_code', 'explanation', 'diff_text',
                  'requires_approval', 'status', 'approved_at', 'applied_at', 'created_at']
        read_only_fields = ['id', 'created_at']


class AppliedChangeSerializer(serializers.ModelSerializer):
    """Serializer for AppliedChange model."""

    class Meta:
        model = AppliedChange
        fields = ['id', 'file_path', 'original_hash', 'new_hash', 'diff_text', 'change_id',
                  'reason', 'related_error_id', 'approved', 'approved_at', 'applied_at', 'rolled_back_at', 'created_at']
        read_only_fields = ['id', 'created_at']
