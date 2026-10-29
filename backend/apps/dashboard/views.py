from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count
from django.contrib.auth import get_user_model
from .models import DebuggingSession, RepairAttempt, VerificationRun

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    """Get dashboard statistics for the current user."""
    user = request.user
    
    total_sessions = DebuggingSession.objects.filter(user=user).count()
    repairs_attempted = RepairAttempt.objects.filter(session__user=user).count()
    
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
    
    return Response({
        'total_sessions': total_sessions,
        'repairs_attempted': repairs_attempted,
        'verified_repairs': verified_repairs,
        'failed_verifications': failed_verifications,
        'recent_sessions': recent_sessions_data,
    })
