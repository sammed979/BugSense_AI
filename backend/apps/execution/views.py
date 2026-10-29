from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from sandbox.python_runner import PythonRunner
from apps.dashboard.models import DebuggingSession


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def execute_code(request):
    """Execute Python code securely."""
    data = request.data
    code = data.get('code') or data.get('source_code', '')
    timeout = data.get('timeout', None)
    session_id = data.get('session_id')

    if not code:
        return Response(
            {'error': 'code is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        exit_code, stdout, stderr, duration_ms = PythonRunner.execute(code, timeout)
        
        # Update session if provided
        if session_id:
            try:
                session = DebuggingSession.objects.get(id=session_id, user=request.user)
                # Only update status if it's still in a pending state
                if session.status in ['CREATED', 'ANALYZING', 'REPAIRING']:
                    session.status = 'FAILED' if exit_code != 0 else 'VERIFIED'
                    session.save()
            except DebuggingSession.DoesNotExist:
                pass
        
        return Response({
            'exit_code': exit_code,
            'stdout': stdout,
            'stderr': stderr,
            'duration_ms': round(duration_ms, 2),
            'timed_out': exit_code == -1
        }, status=status.HTTP_200_OK)
    
    except RuntimeError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        return Response(
            {'error': f'Execution failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
