from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count
from django.contrib.auth import get_user_model
from .models import DebuggingSession, RepairAttempt, VerificationRun, AnalysisResult
from apps.learning.models import LearningActivity
from .models import Project

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """Get dashboard statistics for the current user."""
    user = request.user
    
    total_sessions = DebuggingSession.objects.filter(user=user).count()
    repairs_attempted = RepairAttempt.objects.filter(session__user=user).count()
    total_analyses = AnalysisResult.objects.filter(session__user=user).count()
    logs_explained = DebuggingSession.objects.filter(user=user, language='technical-log').count()
    learning_activities = LearningActivity.objects.filter(user=user).count()
    
    # Count verified repairs (verification runs with PASSED status)
    verified_repairs = VerificationRun.objects.filter(
        repair_attempt__session__user=user,
        execution_status='PASSED'
    ).count()
    
    # Count failed verifications
    failed_verifications = VerificationRun.objects.filter(
        repair_attempt__session__user=user,
        execution_status='FAILED'
    ).count()
    
    # Recent sessions
    recent_sessions = DebuggingSession.objects.filter(
        user=user
    ).order_by('-created_at')[:5]
    
    recent_sessions_data = [
        {
            'id': str(session.id),
            'language': session.language,
            'status': session.status,
            'created_at': session.created_at.isoformat(),
        }
        for session in recent_sessions
    ]

    recent_logs = list(DebuggingSession.objects.filter(user=user, language='technical-log').order_by('-created_at').values('id', 'status', 'created_at', 'error_message')[:5])
    for row in recent_logs:
        row['id'] = str(row['id'])
        row['created_at'] = row['created_at'].isoformat()
        row['summary'] = (row.pop('error_message') or 'Technical log explained').splitlines()[0][:200]
    recent_projects = list(Project.objects.filter(user=user).order_by('-updated_at').values('id', 'name', 'language', 'updated_at')[:5])
    for row in recent_projects:
        row['updated_at'] = row['updated_at'].isoformat()
    completed_lessons = LearningActivity.objects.filter(user=user, activity_type='lesson', completed=True).count()
    
    return Response({
        'total_sessions': total_sessions,
        'total_analyses': total_analyses,
        'logs_explained': logs_explained,
        'learning_activities': learning_activities,
        'repairs_attempted': repairs_attempted,
        'verified_repairs': verified_repairs,
        'failed_verifications': failed_verifications,
        'recent_sessions': recent_sessions_data,
        'recent_logs': recent_logs,
        'recent_projects': recent_projects,
        'completed_lessons': completed_lessons,
    })
