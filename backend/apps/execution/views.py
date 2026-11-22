from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from apps.dashboard.models import DebuggingSession
from django.shortcuts import get_object_or_404

from services.language_detector import LanguageDetector
from sandbox.runners import get_runner, supported_execution_languages


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def execute_code(request):
    """Execute source code securely using the language-appropriate runner.

    The language is auto-detected from the source code. A confident detection
    always wins over the client selection, so a Java program is never run with
    the Python interpreter just because Python is the default.
    """
    data = request.data
    code = data.get('code') or data.get('source_code', '')
    timeout = data.get('timeout', None)
    session_id = data.get('session_id')
    selected_language = data.get('language', '') or ''
    filename = data.get('filename')

    if not isinstance(code, str) or not code.strip():
        return Response(
            {'error': 'code is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    if len(code) > 200_000:
        return Response({'error': 'code exceeds the 200 KB execution limit'}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

    supported = supported_execution_languages()
    detection = LanguageDetector.detect(code, filename=filename)
    if detection.confident and detection.language in supported:
        language = detection.language
    elif selected_language in supported:
        language = selected_language
    else:
        language = detection.language if detection.language in supported else 'python'

    runner = get_runner(language)
    if runner is None:
        return Response(
            {'error': f'Code execution is not supported for language: {language}'},
            status=status.HTTP_400_BAD_REQUEST,
        )

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
        exit_code, stdout, stderr, duration_ms = runner.execute(code, timeout)
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
            'language': language,
            'language_detection': detection.to_dict(),
            'session_id': session.id,
        }, status=status.HTTP_200_OK)
    except RuntimeError:
        session.status = 'EXECUTION_UNAVAILABLE'
        session.save(update_fields=['status', 'updated_at'])
        return Response(
            {'error': 'Code execution is unavailable. Enable and configure the isolated runner on the backend.', 'session_id': session.id},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception:
        session.status = 'FAILED'
        session.save(update_fields=['status', 'updated_at'])
        return Response(
            {'error': 'Code execution failed unexpectedly.', 'session_id': session.id},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
