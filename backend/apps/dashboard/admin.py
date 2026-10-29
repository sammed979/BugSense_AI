from django.contrib import admin
from .models import Project, DebuggingSession, AnalysisResult, RepairAttempt, VerificationRun, FileChange, UserFeedback


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'user', 'language', 'created_at']
    list_filter = ['language', 'source_type', 'created_at']
    search_fields = ['name', 'user__username', 'user__email']


@admin.register(DebuggingSession)
class DebuggingSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'project', 'status', 'language', 'created_at']
    list_filter = ['status', 'language', 'created_at']
    search_fields = ['user__username', 'user__email', 'error_message']


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'error_category', 'confidence', 'created_at']
    list_filter = ['error_category', 'created_at']
    search_fields = ['diagnosis', 'session__error_message']


@admin.register(RepairAttempt)
class RepairAttemptAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'attempt_number', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['session__error_message']


@admin.register(VerificationRun)
class VerificationRunAdmin(admin.ModelAdmin):
    list_display = ['id', 'repair_attempt', 'syntax_status', 'test_status', 'execution_status', 'created_at']
    list_filter = ['syntax_status', 'test_status', 'execution_status', 'created_at']


@admin.register(FileChange)
class FileChangeAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'file_path', 'approved_at', 'applied_at', 'created_at']
    list_filter = ['approved_at', 'applied_at', 'created_at']
    search_fields = ['file_path', 'session__error_message']


@admin.register(UserFeedback)
class UserFeedbackAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'session', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['user__username', 'user__email', 'comment']
