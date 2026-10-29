from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.dashboard.models import DebuggingSession


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def history_list(request):
    """Get debugging history."""
    sessions = DebuggingSession.objects.filter(user=request.user).order_by('-created_at')[:10]
    return Response({
        'sessions': [
            {
                'id': s.id,
                'language': s.language,
                'status': s.status,
                'created_at': s.created_at.isoformat(),
                'source_code': s.source_code,
                'error_message': s.error_message,
                'terminal_logs': s.terminal_logs,
            }
            for s in sessions
        ]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def session_detail(request, session_id):
    """Get details of a specific debugging session."""
    try:
        session = DebuggingSession.objects.get(id=session_id, user=request.user)
        return Response({
            'id': session.id,
            'language': session.language,
            'status': session.status,
            'created_at': session.created_at.isoformat(),
            'source_code': session.source_code,
            'error_message': session.error_message,
            'terminal_logs': session.terminal_logs,
        })
    except DebuggingSession.DoesNotExist:
        return Response({'error': 'Session not found'}, status=404)
