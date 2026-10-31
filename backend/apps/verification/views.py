"""Isolated candidate verification endpoint."""
import asyncio
import logging
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from apps.dashboard.models import DebuggingSession, RepairAttempt, VerificationRun
from services.verification_engine import VerificationEngine

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_repair(request):
    data = request.data
    original_code = data.get('original_code', '')
    repaired_code = data.get('repaired_code', '')
    language = data.get('language', 'python')
    if not isinstance(repaired_code, str) or not repaired_code.strip():
        return Response({'error': 'repaired_code is required'}, status=status.HTTP_400_BAD_REQUEST)
    if language != 'python':
        return Response({'error': 'Only Python verification is currently supported.'}, status=status.HTTP_400_BAD_REQUEST)
    if len(repaired_code) > 200_000:
        return Response({'error': 'source exceeds the 200 KB verification limit'}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
    try:
        result = asyncio.run(VerificationEngine.verify_repair(original_code, repaired_code, language))
        attempt = None
        attempt_id = data.get('attempt_id')
        if attempt_id:
            attempt = get_object_or_404(RepairAttempt, id=attempt_id, session__user=request.user)
        elif data.get('session_id'):
            session = get_object_or_404(DebuggingSession, id=data['session_id'], user=request.user)
            attempt = session.repairs.filter(proposed_patch=repaired_code).order_by('-created_at').first()
        if attempt:
            VerificationRun.objects.create(
                repair_attempt=attempt,
                syntax_status=result.get('syntax_check'), lint_status=result.get('lint_check'),
                execution_status=result.get('status'), test_status=result.get('status'),
                exit_code=(result.get('execution_result') or {}).get('exit_code'),
                duration_ms=round((result.get('execution_result') or {}).get('duration_ms', 0)),
                stdout=(result.get('execution_result') or {}).get('stdout', ''),
                stderr=(result.get('execution_result') or {}).get('stderr', ''),
            )
            attempt.status = 'VERIFIED' if result.get('status') == 'passed' else ('FAILED' if result.get('status') == 'failed' else 'PENDING')
            attempt.save(update_fields=['status'])
            result['attempt_id'] = attempt.id
        return Response(result, status=status.HTTP_200_OK)
    except Exception:
        logger.exception('Verification failed for user_id=%s', request.user.id)
        return Response({'error': 'Verification could not complete in the isolated runner.', 'status': 'blocked'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
