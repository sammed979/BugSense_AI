from rest_framework import serializers
from .models import Project, ProjectFile


class ProjectSerializer(serializers.ModelSerializer):
    """Serializer for Project model."""

    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProjectFileSerializer(serializers.ModelSerializer):
    """Serializer for ProjectFile model."""

    class Meta:
        model = ProjectFile
        fields = ['id', 'file_path', 'file_name', 'file_content', 'language', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
