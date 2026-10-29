from django.db import models
from django.conf import settings


class Project(models.Model):
    """User projects for code debugging."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=50)  # 'upload', 'paste', 'local_agent'
    language = models.CharField(max_length=50, default='python')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'projects'


class DebuggingSession(models.Model):
    """Debugging sessions tracking user interactions."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sessions')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True, related_name='sessions')
    error_message = models.TextField(null=True, blank=True)
    terminal_logs = models.TextField(null=True, blank=True)
    source_code = models.TextField(null=True, blank=True)
    language = models.CharField(max_length=50, default='python')
    status = models.CharField(max_length=50, default='CREATED')  # CREATED, ANALYZING, REPAIRING, VERIFIED, FAILED
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'debugging_sessions'


class AnalysisResult(models.Model):
    """Results from code analysis."""
    session = models.ForeignKey(DebuggingSession, on_delete=models.CASCADE, related_name='analyses')
    diagnosis = models.TextField()
    evidence_json = models.JSONField(null=True, blank=True)
    error_category = models.CharField(max_length=100, null=True, blank=True)
    affected_file = models.CharField(max_length=255, null=True, blank=True)
    affected_line = models.IntegerField(null=True, blank=True)
    confidence = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'analysis_results'


class RepairAttempt(models.Model):
    """Repair attempts for debugging sessions."""
    session = models.ForeignKey(DebuggingSession, on_delete=models.CASCADE, related_name='repairs')
    attempt_number = models.IntegerField()
    proposed_patch = models.TextField()
    status = models.CharField(max_length=50)  # PENDING, APPLIED, VERIFIED, FAILED
    failure_summary = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'repair_attempts'


class VerificationRun(models.Model):
    """Verification results for repair attempts."""
    repair_attempt = models.ForeignKey(RepairAttempt, on_delete=models.CASCADE, related_name='verifications')
    syntax_status = models.CharField(max_length=50, null=True, blank=True)
    lint_status = models.CharField(max_length=50, null=True, blank=True)
    test_status = models.CharField(max_length=50, null=True, blank=True)
    execution_status = models.CharField(max_length=50, null=True, blank=True)
    exit_code = models.IntegerField(null=True, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    stdout = models.TextField(null=True, blank=True)
    stderr = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'verification_runs'


class FileChange(models.Model):
    """File changes from repairs."""
    session = models.ForeignKey(DebuggingSession, on_delete=models.CASCADE, related_name='file_changes')
    file_path = models.CharField(max_length=255)
    original_hash = models.CharField(max_length=64)
    new_hash = models.CharField(max_length=64)
    diff_text = models.TextField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    rolled_back_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'file_changes'


class UserFeedback(models.Model):
    """User feedback on debugging sessions."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='feedback')
    session = models.ForeignKey(DebuggingSession, on_delete=models.CASCADE, related_name='feedback')
    rating = models.IntegerField(null=True, blank=True)  # 1-5
    comment = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_feedback'

