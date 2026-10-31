"""Authenticated repair proposal endpoint."""
import asyncio
import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.dashboard.models import DebuggingSession, RepairAttempt
from services.code_analyzer import CodeAnalyzer
from services.repair_engine import RepairEngine

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_repair(request):
    """Generate an AI repair only after explicit consent; Quick Fix is opt-in."""
    data = request.data
    source_code = data.get('source_code', '')
    error_message = data.get('error_message', '')
    traceback_text = data.get('traceback', '')
    diagnosis = data.get('diagnosis') or {}
    language = data.get('language', 'python')
    session_id = data.get('session_id')
    use_heuristic = data.get('use_heuristic') is True
    allow_external_ai = data.get('allow_external_ai') is True

    if not isinstance(source_code, str) or not source_code.strip():
        return Response({'error': 'source_code is required'}, status=status.HTTP_400_BAD_REQUEST)
    if len(source_code) > 200_000:
        return Response({'error': 'source_code exceeds the 200 KB repair limit'}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
    if language != 'python':
        return Response({'error': 'Only Python repair is currently supported'}, status=status.HTTP_400_BAD_REQUEST)
    from services.provider_router import settings_for
    provider_settings = settings_for(request.user)
    selected_mode = provider_settings.mode
    if not use_heuristic and selected_mode != 'local' and not allow_external_ai:
        return Response({
            'error': 'Consent is required before sending source code to the configured AI provider.',
            'error_type': 'consent_required',
            'source': 'error',
        }, status=status.HTTP_403_FORBIDDEN)

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
            ))

        repair_result['session_id'] = session.id
        if repair_result.get('error') or repair_result.get('success') is False:
            session.status = 'REPAIR_FAILED'
            session.save(update_fields=['status', 'updated_at'])
            error_type = repair_result.get('error_type', 'provider_error')
            http_status = status.HTTP_422_UNPROCESSABLE_ENTITY if error_type == 'unsupported_or_ambiguous' else status.HTTP_429_TOO_MANY_REQUESTS if error_type in ('quota_exhausted', 'rate_limited') else status.HTTP_503_SERVICE_UNAVAILABLE if error_type in ('network', 'timeout', 'service_unavailable', 'missing_api_key') else status.HTTP_502_BAD_GATEWAY
            return Response(repair_result, status=http_status)

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
        return Response(repair_result, status=status.HTTP_200_OK)
    except asyncio.TimeoutError:
        session.status = 'REPAIR_FAILED'
        session.save(update_fields=['status', 'updated_at'])
        return Response({
            'error': 'The AI repair request timed out. Your original code was not changed.',
            'error_type': 'timeout',
            'repaired_code': source_code,
            'source': 'error',
            'session_id': session.id,
        }, status=status.HTTP_504_GATEWAY_TIMEOUT)
    except Exception:
        logger.exception('Repair failed for user_id=%s session_id=%s', request.user.id, session.id)
        session.status = 'REPAIR_FAILED'
        session.save(update_fields=['status', 'updated_at'])
        return Response({
            'error': 'Repair generation failed unexpectedly. The original code was not changed.',
            'error_type': 'internal_error',
            'source': 'error',
            'session_id': session.id,
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
