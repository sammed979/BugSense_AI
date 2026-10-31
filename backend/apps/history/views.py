from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.dashboard.models import DebuggingSession
from django.core.paginator import Paginator
from django.db.models import Q
from apps.dashboard.models import VerificationRun


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def history_list(request):
    """Get searchable, user-scoped debugging history with verification summaries."""
    sessions = DebuggingSession.objects.filter(user=request.user)
    search = request.query_params.get('search', '').strip()
    status_filter = request.query_params.get('status', '').strip()
    language = request.query_params.get('language', '').strip()
    date_from = request.query_params.get('date_from', '').strip()
    date_to = request.query_params.get('date_to', '').strip()
    if search:
        sessions = sessions.filter(Q(error_message__icontains=search) | Q(source_code__icontains=search) | Q(terminal_logs__icontains=search))
    if status_filter:
        sessions = sessions.filter(status__iexact=status_filter)
    if language:
        sessions = sessions.filter(language__iexact=language)
    if date_from:
        sessions = sessions.filter(created_at__date__gte=date_from)
    if date_to:
        sessions = sessions.filter(created_at__date__lte=date_to)
    page = Paginator(sessions.order_by('-created_at'), 10).get_page(request.query_params.get('page', 1))
    rows = []
    for s in page.object_list:
        verification = VerificationRun.objects.filter(repair_attempt__session=s).order_by('-created_at').first()
        lines = (s.error_message or '').splitlines()
        rows.append({
            'id': s.id, 'language': s.language, 'status': s.status,
            'created_at': s.created_at.isoformat(), 'source_code': s.source_code,
            'error_message': s.error_message, 'error_summary': (lines[0] if lines else '')[:240],
            'terminal_logs': s.terminal_logs,
            'verification_status': verification.execution_status if verification else None,
        })
    return Response({
        'sessions': rows, 'page': page.number, 'pages': page.paginator.num_pages,
        'total': page.paginator.count, 'has_next': page.has_next(), 'has_previous': page.has_previous(),
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
