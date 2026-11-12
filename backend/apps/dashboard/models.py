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


class ProjectFile(models.Model):
    """Text source files retained for a user's project explorer."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='files')
    path = models.CharField(max_length=512)
    content = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'project_files'
        constraints = [models.UniqueConstraint(fields=['project', 'path'], name='unique_project_file_path')]
        ordering = ['path']


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


class ProjectAnalysis(models.Model):
    """Project-level analysis results."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='analyses')
    analysis_type = models.CharField(max_length=50)  # 'static', 'ai', 'cross_file'
    status = models.CharField(max_length=50, default='pending')  # pending, in_progress, completed, failed
    total_files = models.IntegerField(default=0)
    analyzed_files = models.IntegerField(default=0)
    summary = models.JSONField(default=dict)  # languages, frameworks, counts
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'project_analyses'
        ordering = ['-created_at']


class ProjectIssue(models.Model):
    """Issues found during project analysis."""
    analysis = models.ForeignKey(ProjectAnalysis, on_delete=models.CASCADE, related_name='issues')
    issue_id = models.CharField(max_length=100, unique=True)
    severity = models.CharField(max_length=20)  # critical, high, medium, low, informational
    category = models.CharField(max_length=100)  # syntax_error, missing_import, type_mismatch, etc.
    affected_file = models.CharField(max_length=512)
    line_number = models.IntegerField(null=True, blank=True)
    line_range_end = models.IntegerField(null=True, blank=True)
    explanation = models.TextField()
    supporting_evidence = models.JSONField(default=list)
    related_files = models.JSONField(default=list)
    root_cause = models.TextField(null=True, blank=True)
    suggested_solution = models.TextField()
    confidence = models.IntegerField(default=0)  # 0-100
    status = models.CharField(max_length=50, default='pending')  # pending, approved, rejected, applied
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'project_issues'
        ordering = ['-severity', 'created_at']


class FileDependency(models.Model):
    """Dependencies between project files."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='dependencies')
    source_file = models.CharField(max_length=512)
    target_file = models.CharField(max_length=512)
    dependency_type = models.CharField(max_length=50)  # import, require, template, url, model, etc.
    line_number = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'file_dependencies'
        unique_together = [['project', 'source_file', 'target_file', 'dependency_type']]


class SuggestedFix(models.Model):
    """Suggested fixes for project issues."""
    issue = models.ForeignKey(ProjectIssue, on_delete=models.CASCADE, related_name='suggested_fixes')
    original_code = models.TextField()
    suggested_code = models.TextField()
    explanation = models.TextField()
    diff_text = models.TextField()
    requires_approval = models.BooleanField(default=True)
    status = models.CharField(max_length=50, default='pending')  # pending, approved, rejected, applied
    approved_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'suggested_fixes'
        ordering = ['-created_at']


class AppliedChange(models.Model):
    """Changes applied to project files."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='applied_changes')
    issue = models.ForeignKey(ProjectIssue, on_delete=models.CASCADE, related_name='applied_changes', null=True, blank=True)
    file_path = models.CharField(max_length=512)
    original_hash = models.CharField(max_length=64)
    new_hash = models.CharField(max_length=64)
    diff_text = models.TextField(null=True, blank=True)
    change_id = models.CharField(max_length=100, unique=True)
    reason = models.TextField()
    related_error_id = models.CharField(max_length=100, null=True, blank=True)
    approved = models.BooleanField(default=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    rolled_back_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'applied_changes'
        ordering = ['-created_at']

