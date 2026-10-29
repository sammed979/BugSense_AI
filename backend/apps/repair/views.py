from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from services.repair_engine import RepairEngine
from services.code_analyzer import CodeAnalyzer
from apps.dashboard.models import DebuggingSession, RepairAttempt
import asyncio
import json


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_repair(request):
    """Generate and verify a code repair using AI."""
    print(f"=== Repair Request Received ===")
    print(f"Request data keys: {request.data.keys() if hasattr(request.data, 'keys') else 'not a dict'}")
    
    data = request.data if isinstance(request.data, dict) else json.loads(request.data) if isinstance(request.data, str) else request.data

    source_code = data.get('source_code', '')
    error_message = data.get('error_message', '')
    diagnosis = data.get('diagnosis', {})
    language = data.get('language', 'python')
    session_id = data.get('session_id')
    use_heuristic = data.get('use_heuristic', False)

    print(f"Source code length: {len(source_code)}")
    print(f"Error message: {error_message[:100] if error_message else 'None'}")
    print(f"Use heuristic: {use_heuristic}")

    if not source_code:
        return Response(
            {'error': 'source_code is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Get or create debugging session
        session = None
        if session_id:
            try:
                session = DebuggingSession.objects.get(id=session_id, user=request.user)
            except DebuggingSession.DoesNotExist:
                pass
        
        if not session:
            session = DebuggingSession.objects.create(
                user=request.user,
                source_code=source_code,
                error_message=error_message,
                language=language,
                status='REPAIRING'
            )

        # Count existing repairs for this session
        attempt_number = RepairAttempt.objects.filter(session=session).count() + 1

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        if use_heuristic:
            # Use heuristic repair explicitly requested (synchronous, no async needed)
            from services.code_analyzer import CodeAnalyzer
            enhanced_diagnosis = CodeAnalyzer.analyze_error_context(source_code, error_message)
            repair_result = RepairEngine._generate_heuristic_repair(source_code, error_message, enhanced_diagnosis)
        else:
            # Use AI repair (async)
            repair_result = loop.run_until_complete(
                RepairEngine.generate_repair(source_code, error_message, diagnosis, language)
            )
        
        loop.close()

        # Save repair attempt to database
        repair_attempt = RepairAttempt.objects.create(
            session=session,
            attempt_number=attempt_number,
            proposed_patch=repair_result.get('repaired_code', source_code),
            status='PENDING'
        )

        # Add attempt info to response
        repair_result['attempt_id'] = repair_attempt.id
        repair_result['session_id'] = session.id

        return Response(repair_result, status=status.HTTP_200_OK)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response(
            {'error': f'Repair generation failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
