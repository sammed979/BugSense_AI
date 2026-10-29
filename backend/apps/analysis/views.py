from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from services.error_parser import ErrorParser
from services.code_analyzer import CodeAnalyzer
from services.ai_service import AIService
from apps.dashboard.models import DebuggingSession, AnalysisResult
import asyncio
import json

User = get_user_model()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_analysis(request):
    """Analyze code and diagnostic evidence."""
    try:
        data = request.data
        error_message = data.get('error_message', '')
        terminal_logs = data.get('terminal_logs', '')
        source_code = data.get('source_code', '')
        language = data.get('language', 'python')
        session_id = data.get('session_id')

        if not source_code:
            return Response(
                {'error': 'source_code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

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
                terminal_logs=terminal_logs,
                language=language,
                status='ANALYZING'
            )

        # Static analysis
        syntax_errors = []
        lint_issues = []
        undefined_names = []

        if language == 'python':
            syntax_errors = CodeAnalyzer.check_syntax(source_code)
            undefined_names = CodeAnalyzer.extract_undefined_names(source_code)
            lint_issues = CodeAnalyzer.run_ruff(source_code)

        # Parse traceback
        parsed_traceback = None
        if terminal_logs:
            parsed_traceback = ErrorParser.parse_traceback(terminal_logs)

        # Extract error type
        error_type = ErrorParser.extract_error_type(error_message)

        # AI analysis (if configured)
        ai_result = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            ai_result = loop.run_until_complete(
                AIService.analyze_error(error_message, terminal_logs, source_code, language)
            )
            loop.close()
        except Exception as e:
            ai_result = {'error': f'AI analysis failed: {str(e)}'}

        # Build analysis result
        result = {
            'static_analysis': {
                'syntax_errors': [
                    {'line': e.line, 'column': e.column, 'message': e.message}
                    for e in syntax_errors
                ],
                'undefined_names': undefined_names,
                'lint_issues': [
                    {
                        'code': i.code,
                        'message': i.message,
                        'line': i.line,
                        'column': i.column,
                        'severity': i.severity
                    }
                    for i in lint_issues
                ]
            },
            'traceback_analysis': None,
            'ai_analysis': ai_result
        }

        if parsed_traceback:
            result['traceback_analysis'] = {
                'exception_type': parsed_traceback.exception_type,
                'exception_message': parsed_traceback.exception_message,
                'frames': [
                    {
                        'file_path': f.file_path,
                        'line_number': f.line_number,
                        'function_name': f.function_name,
                        'code_line': f.code_line
                    }
                    for f in parsed_traceback.frames
                ]
            }

        # Save analysis result to database
        analysis_result = AnalysisResult.objects.create(
            session=session,
            diagnosis=json.dumps(ai_result) if ai_result else 'No diagnosis',
            evidence_json=result.get('static_analysis'),
            error_category=ai_result.get('error_category') if ai_result else None,
            confidence=ai_result.get('confidence') if ai_result else None
        )

        # Add session ID to response
        result['session_id'] = session.id
        result['analysis_id'] = analysis_result.id

        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': f'Analysis failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
