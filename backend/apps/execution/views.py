from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from sandbox.python_runner import PythonRunner
from apps.dashboard.models import DebuggingSession
from django.shortcuts import get_object_or_404


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def execute_code(request):
    """Execute Python code securely."""
    data = request.data
    code = data.get('code') or data.get('source_code', '')
    timeout = data.get('timeout', None)
    session_id = data.get('session_id')
    language = data.get('language', 'python')

    if not isinstance(code, str) or not code.strip():
        return Response(
            {'error': 'code is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    if len(code) > 200_000:
        return Response({'error': 'code exceeds the 200 KB execution limit'}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
    if language != 'python':
        return Response({'error': 'Only Python execution is currently supported'}, status=status.HTTP_400_BAD_REQUEST)

    if session_id:
        session = get_object_or_404(DebuggingSession, id=session_id, user=request.user)
        session.source_code = code
        session.language = language
        session.status = 'RUNNING'
        session.save(update_fields=['source_code', 'language', 'status', 'updated_at'])
    else:
        session = DebuggingSession.objects.create(
            user=request.user,
            source_code=code,
            language=language,
            status='RUNNING',
        )

    try:
        exit_code, stdout, stderr, duration_ms = PythonRunner.execute(code, timeout)
        session.error_message = stderr or ''
        session.terminal_logs = stderr or stdout or ''
        session.status = 'FAILED' if exit_code != 0 else 'EXECUTED'
        session.save(update_fields=['error_message', 'terminal_logs', 'status', 'updated_at'])
        return Response({
            'exit_code': exit_code,
            'stdout': stdout,
            'stderr': stderr,
            'duration_ms': round(duration_ms, 2),
            'timed_out': exit_code == -1,
            'session_id': session.id,
        }, status=status.HTTP_200_OK)
    except RuntimeError:
        session.status = 'EXECUTION_UNAVAILABLE'
        session.save(update_fields=['status', 'updated_at'])
        return Response(
            {'error': 'Code execution is unavailable. Enable and configure the isolated Python runner on the backend.', 'session_id': session.id},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception:
        session.status = 'FAILED'
        session.save(update_fields=['status', 'updated_at'])
        return Response(
            {'error': 'Code execution failed unexpectedly.', 'session_id': session.id},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
