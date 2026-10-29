from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from services.verification_engine import VerificationEngine
import asyncio


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_repair(request):
    """Verify a code repair."""
    data = request.data
    original_code = data.get('original_code', '')
    repaired_code = data.get('repaired_code', '')
    language = data.get('language', 'python')

    if not repaired_code:
        return Response(
            {'error': 'repaired_code is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        verification_result = loop.run_until_complete(
            VerificationEngine.verify_repair(original_code, repaired_code, language)
        )
        loop.close()

        return Response(verification_result, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response(
            {'error': f'Verification failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
