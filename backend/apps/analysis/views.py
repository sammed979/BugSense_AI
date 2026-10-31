"""Static and optional AI-assisted code analysis endpoints."""
import asyncio
import json
import logging
import shutil

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.dashboard.models import AnalysisResult, DebuggingSession
from services.ai_service import AIService
from services.code_analyzer import CodeAnalyzer
from services.error_parser import ErrorParser
from sandbox.python_runner import PythonRunner

logger = logging.getLogger(__name__)
User = get_user_model()


@api_view(['GET'])
@permission_classes([AllowAny])
def ai_provider_health(request):
    """Report backend, static analysis, execution and real Gemini model readiness."""
    try:
        connection.ensure_connection()
        database_status = 'available'
    except Exception:
        database_status = 'unavailable'

    try:
        static_ok = not CodeAnalyzer.check_syntax('value = 1\nprint(value)') and not CodeAnalyzer.extract_undefined_names('value = 1\nprint(value)')
    except Exception:
        static_ok = False

    execution = cache.get('bugsense_execution_readiness')
    if execution is None:
        execution_enabled = bool(getattr(settings, 'EXECUTION_ENABLED', False))
        python_available = bool(shutil.which('python') or shutil.which('python3'))
        if not execution_enabled:
            execution = {'status': 'disabled', 'ready': False, 'enabled': False}
        elif not python_available:
            execution = {'status': 'python_unavailable', 'ready': False, 'enabled': True}
        else:
            try:
                exit_code, stdout, _stderr, _duration = PythonRunner.execute("print('bugsense-health')", timeout=2)
                healthy = exit_code == 0 and stdout.strip() == 'bugsense-health'
                execution = {'status': 'ready' if healthy else 'unavailable', 'ready': healthy, 'enabled': True}
            except Exception:
                execution = {'status': 'unavailable', 'ready': False, 'enabled': True}
        cache.set('bugsense_execution_readiness', execution, 60)
    gemini = cache.get('bugsense_gemini_model_access')
    if gemini is None:
        gemini = AIService.check_gemini_model_access()
        cache.set('bugsense_gemini_model_access', gemini, 60)

    return Response({
        'backend': {'status': 'available', 'ready': True},
        'database': {'status': database_status, 'ready': database_status == 'available'},
        'static_analyzer': {'status': 'ready' if static_ok else 'unavailable', 'ready': static_ok},
        'execution': execution,
        'ai': {
            'provider': AIService.readiness()['provider'],
            'model': AIService.readiness()['model'],
            'configured': AIService.readiness()['configured'],
            **gemini,
        },
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_analysis(request):
    """Return static findings even when optional external AI is unavailable."""
    data = request.data
    source_code = data.get('source_code', '')
    language = data.get('language', 'python')
    error_message = data.get('error_message', '')
    terminal_logs = data.get('terminal_logs', '')
    allow_external_ai = data.get('allow_external_ai') is True

    if not isinstance(source_code, str) or not source_code.strip():
        return Response({'error': 'source_code is required'}, status=status.HTTP_400_BAD_REQUEST)
    if len(source_code) > 200_000:
        return Response({'error': 'source_code exceeds the 200 KB analysis limit'}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
    if language not in ('python',):
        return Response({'error': 'Only Python analysis is currently supported'}, status=status.HTTP_400_BAD_REQUEST)

    session_id = data.get('session_id')
    if session_id:
        session = get_object_or_404(DebuggingSession, id=session_id, user=request.user)
        session.source_code = source_code
        session.language = language
        session.error_message = error_message
        session.terminal_logs = terminal_logs
        session.save(update_fields=['source_code', 'language', 'error_message', 'terminal_logs', 'updated_at'])
    else:
        session = DebuggingSession.objects.create(
            user=request.user,
            source_code=source_code,
            error_message=error_message,
            terminal_logs=terminal_logs,
            language=language,
            status='ANALYZING',
        )

    static_result = {
        'status': 'complete',
        'syntax_errors': [],
        'undefined_names': [],
        'lint_issues': [],
    }
    try:
        syntax_errors = CodeAnalyzer.check_syntax(source_code)
        undefined_names = CodeAnalyzer.extract_undefined_names(source_code)
        lint_issues = CodeAnalyzer.run_ruff(source_code)
        static_result.update({
            'syntax_errors': [
                {'line': error.line, 'column': error.column, 'message': error.message}
                for error in syntax_errors
            ],
            'undefined_names': undefined_names,
            'lint_issues': [
                {
                    'code': issue.code,
                    'message': issue.message,
                    'line': issue.line,
                    'column': issue.column,
                    'severity': issue.severity,
                }
                for issue in lint_issues
            ],
        })
    except Exception:
        logger.exception('Static analysis failed for user_id=%s', request.user.id)
        static_result['status'] = 'failed'
        static_result['error'] = 'Static analysis could not complete.'

    traceback_analysis = None
    runtime_diagnosis = None
    if terminal_logs:
        try:
            runtime_diagnosis = CodeAnalyzer.analyze_error_context(source_code, error_message or terminal_logs)
            parsed = ErrorParser.parse_traceback(terminal_logs)
            if parsed:
                traceback_analysis = {
                    'exception_type': parsed.exception_type,
                    'exception_message': parsed.exception_message,
                    'frames': [
                        {
                            'file_path': frame.file_path,
                            'line_number': frame.line_number,
                            'function_name': frame.function_name,
                            'code_line': frame.code_line,
                        }
                        for frame in parsed.frames
                    ],
                }
        except Exception:
            logger.exception('Traceback parsing failed for user_id=%s', request.user.id)

    from services.provider_router import settings_for
    provider_settings = settings_for(request.user)
    selected_mode = provider_settings.mode
    if allow_external_ai or selected_mode == 'local':
        try:
            from services.provider_router import analyze
            ai_result = asyncio.run(analyze(request.user, error_message, terminal_logs, source_code, language, provider_settings=provider_settings))
            if ai_result.get('error'):
                ai_result['status'] = 'failed'
            else:
                ai_result['status'] = 'complete'
        except Exception as exc:
            error_type = 'timeout' if isinstance(exc, asyncio.TimeoutError) else 'provider_error'
            ai_result = {
                'status': 'failed',
                'error': 'AI analysis could not complete.',
                'error_type': error_type,
            }
    else:
        ai_result = {
            'status': 'consent_required' if selected_mode != 'local' else 'unavailable',
            'message': 'Static findings are available. Allow external AI processing to request an AI diagnosis.' if selected_mode != 'local' else 'Local diagnosis is available through static findings.',
            'provider': selected_mode,
        }

    analysis_status = 'complete' if ai_result.get('status') == 'complete' else 'partial'
    try:
        confidence = ai_result.get('confidence')
        if not isinstance(confidence, int):
            confidence = None
        AnalysisResult.objects.create(
            session=session,
            diagnosis=json.dumps(ai_result),
            evidence_json=static_result,
            error_category=ai_result.get('error_category'),
            affected_file=ai_result.get('affected_file'),
            affected_line=ai_result.get('affected_line') if isinstance(ai_result.get('affected_line'), int) else None,
            confidence=confidence,
        )
        session.status = 'ANALYZED' if analysis_status == 'complete' else 'ANALYSIS_PARTIAL'
        session.save(update_fields=['status', 'updated_at'])
    except Exception:
        logger.exception('Could not persist analysis for user_id=%s session_id=%s', request.user.id, session.id)

    return Response({
        'analysis_status': analysis_status,
        'static_analysis': static_result,
        'runtime_diagnosis': runtime_diagnosis,
        'traceback_analysis': traceback_analysis,
        'ai_analysis': ai_result,
        'session_id': session.id,
    }, status=status.HTTP_200_OK)
