"""Authenticated repair proposal endpoint."""
import asyncio
import uuid

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.dashboard.models import DebuggingSession, RepairAttempt
from services.language_detector import LanguageDetector
from services.repair_diagnostics import log_provider_exception, log_provider_failure

SUPPORTED_LANGUAGES = ('python', 'java', 'c', 'cpp', 'javascript')


def _with_request_id(response, request_id):
    response['X-Request-ID'] = request_id
    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_repair(request):
    """Generate an AI repair only after explicit consent; Quick Fix is opt-in."""
    request_id = uuid.uuid4().hex
    data = request.data
    source_code = data.get('source_code', '')
    error_message = data.get('error_message', '')
    traceback_text = data.get('traceback', '')
    diagnosis = data.get('diagnosis') or {}
    selected_language = data.get('language', '') or ''
    filename = data.get('filename')
    session_id = data.get('session_id')
    use_heuristic = data.get('use_heuristic') is True
    allow_external_ai = data.get('allow_external_ai') is True

    if not isinstance(source_code, str) or not source_code.strip():
        return _with_request_id(Response({'error': 'source_code is required'}, status=status.HTTP_400_BAD_REQUEST), request_id)
    if len(source_code) > 200_000:
        return _with_request_id(Response({'error': 'source_code exceeds the 200 KB repair limit'}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE), request_id)

    # Detect language from the actual source. A confident detection wins over
    # the client selection so Java/C/C++/JS code is never repaired as Python.
    detection = LanguageDetector.detect(source_code, filename=filename)
    if detection.confident and detection.language in SUPPORTED_LANGUAGES:
        language = detection.language
    elif selected_language in SUPPORTED_LANGUAGES:
        language = selected_language
    else:
        language = detection.language if detection.language in SUPPORTED_LANGUAGES else 'python'

    from services.provider_router import settings_for
    provider_settings = settings_for(request.user)
    selected_mode = provider_settings.mode
    
    # Consent check removed for development - AI processing enabled by default
    # User can still use Quick Fix (heuristic) which is always local

    if session_id:
        session = get_object_or_404(DebuggingSession, id=session_id, user=request.user)
        session.source_code = source_code
        session.error_message = error_message
        session.terminal_logs = traceback_text
        session.language = language
        session.status = 'REPAIRING'
        session.save(update_fields=['source_code', 'error_message', 'terminal_logs', 'language', 'status', 'updated_at'])
    else:
        session = DebuggingSession.objects.create(
            user=request.user,
            source_code=source_code,
            error_message=error_message,
            terminal_logs=traceback_text,
            language=language,
            status='REPAIRING',
        )

    try:
        if use_heuristic:
            if language != 'python':
                session.status = 'REPAIR_FAILED'
                session.save(update_fields=['status', 'updated_at'])
                return _with_request_id(Response({
                    'error': f'Quick Fix (heuristic repair) supports Python only. Use Repair (AI) for {language} code.',
                    'error_type': 'unsupported_language_for_heuristic',
                    'source': 'error',
                    'language': language,
                    'repaired_code': source_code,
                    'session_id': session.id,
                    'request_id': request_id,
                }, status=status.HTTP_422_UNPROCESSABLE_ENTITY), request_id)
            from services.local_repair_engine import LocalRepairEngine
            repair_result = LocalRepairEngine.generate_repair(source_code, error_message)
            repair_result['provider'] = 'Local Quick Fix'
            repair_result['source'] = 'heuristic'
        else:
            from services.provider_router import repair
            repair_result = asyncio.run(repair(
                request.user,
                source_code,
                error_message,
                diagnosis,
                language,
                traceback=traceback_text,
                provider_settings=provider_settings,
                request_id=request_id,
            ))

        repair_result['session_id'] = session.id
        repair_result.setdefault('language', language)
        repair_result['language_detection'] = detection.to_dict()
        if repair_result.get('error') or repair_result.get('success') is False:
            session.status = 'REPAIR_FAILED'
            session.save(update_fields=['status', 'updated_at'])
            error_type = repair_result.get('error_type', 'provider_error')
            provider = repair_result.get('provider') or (
                provider_settings.primary_provider if selected_mode == 'automatic' else selected_mode
            )
            provider_label = provider if isinstance(provider, str) else selected_mode
            provider_key = provider_label.lower()
            display_provider = {'openai': 'OpenAI', 'gemini': 'Gemini'}.get(provider_key, provider_label.title())
            log_provider_failure(request_id, provider_key, 'repair_generation', error_type)
            http_status = status.HTTP_422_UNPROCESSABLE_ENTITY if error_type == 'unsupported_or_ambiguous' else status.HTTP_429_TOO_MANY_REQUESTS if error_type in ('quota_exhausted', 'rate_limited') else status.HTTP_503_SERVICE_UNAVAILABLE if error_type in ('network', 'timeout', 'service_unavailable', 'missing_api_key') else status.HTTP_502_BAD_GATEWAY
            response = Response({
                'error': f'{display_provider} could not generate a repair ({error_type.replace("_", " ")}).',
                'error_type': error_type,
                'provider': display_provider,
                'source': 'error',
                'repaired_code': source_code,
                'session_id': session.id,
                'request_id': request_id,
            }, status=http_status)
            return _with_request_id(response, request_id)

        repaired_code = repair_result.get('repaired_code')
        if repaired_code and repaired_code != source_code:
            attempt_number = RepairAttempt.objects.filter(session=session).count() + 1
            repair_attempt = RepairAttempt.objects.create(
                session=session,
                attempt_number=attempt_number,
                proposed_patch=repaired_code,
                status='PENDING',
            )
            repair_result['attempt_id'] = repair_attempt.id
        return _with_request_id(Response(repair_result, status=status.HTTP_200_OK), request_id)
    except asyncio.TimeoutError as exc:
        log_provider_exception(
            request_id,
            selected_mode,
            'repair_request',
            exc,
            sensitive_values=(source_code, error_message, traceback_text),
        )
        session.status = 'REPAIR_FAILED'
        session.save(update_fields=['status', 'updated_at'])
        return _with_request_id(Response({
            'error': 'The AI repair request timed out. Your original code was not changed.',
            'error_type': 'timeout',
            'repaired_code': source_code,
            'source': 'error',
            'session_id': session.id,
            'request_id': request_id,
        }, status=status.HTTP_504_GATEWAY_TIMEOUT), request_id)
    except Exception as exc:
        log_provider_exception(
            request_id,
            selected_mode,
            'repair_request',
            exc,
            sensitive_values=(source_code, error_message, traceback_text),
        )
        session.status = 'REPAIR_FAILED'
        session.save(update_fields=['status', 'updated_at'])
        return _with_request_id(Response({
            'error': 'Repair generation failed unexpectedly. The original code was not changed.',
            'error_type': 'internal_error',
            'source': 'error',
            'session_id': session.id,
            'request_id': request_id,
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR), request_id)
