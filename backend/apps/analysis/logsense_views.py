"""Independent log explanation API. Uploaded content is parsed as text and never executed."""
import asyncio
import json
from pathlib import Path
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from apps.dashboard.models import AnalysisResult, DebuggingSession
from services.log_sense import MAX_LOG_CHARS, explain_local, redact_secrets


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def explain_log(request):
    upload = request.FILES.get('file')
    if upload:
        if Path(upload.name).suffix.lower() not in ('.txt', '.log'):
            return Response({'error':'Upload a .txt or .log text file.'}, status=status.HTTP_400_BAD_REQUEST)
        if upload.size > 1_000_000:
            return Response({'error':'Log files are limited to 1 MB.'}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        try: log = upload.read().decode('utf-8-sig')
        except UnicodeDecodeError: return Response({'error':'The log file must be UTF-8 text.'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        log = request.data.get('log', '')
    if not isinstance(log, str) or not log.strip(): return Response({'error':'Paste a log or upload a .txt/.log file.'}, status=status.HTTP_400_BAD_REQUEST)
    if len(log) > MAX_LOG_CHARS: return Response({'error':'Logs are limited to 100,000 characters.'}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
    level = request.data.get('explanation_level', 'beginner')
    language = request.data.get('explanation_language', 'en')
    if level not in ('beginner','intermediate','advanced'): return Response({'error':'Invalid explanation level.'}, status=status.HTTP_400_BAD_REQUEST)
    if language not in ('en','kn'): return Response({'error':'Choose English or Kannada.'}, status=status.HTTP_400_BAD_REQUEST)
    redacted, redaction_types = redact_secrets(log)
    # Analyze the redacted copy so secrets cannot enter line explanations or history.
    result = explain_local(redacted, level, language)
    result['original_log'] = log
    result['redactions'] = redaction_types
    result['external_processing'] = False
    from services.provider_router import settings_for
    prefs = settings_for(request.user)
    consent = request.data.get('allow_external_ai') is True or str(request.data.get('allow_external_ai','')).lower() in ('true','1','on')
    if consent and prefs.mode != 'local':
        try:
            from services.provider_router import analyze
            question = request.data.get('question', '')
            prompt = question if isinstance(question, str) and question.strip() else 'Interpret this technical log. Explain evidence, likely causes and uncertainty.'
            ai = asyncio.run(analyze(request.user, prompt, redacted, redacted, f'technical log; explanation language={language}; level={level}', provider_settings=prefs))
            result['ai_interpretation'] = ai
            result['external_processing'] = True
            if ai.get('status') == 'complete': result['provider'] = ai.get('provider', 'Configured provider')
        except Exception:
            result['ai_interpretation'] = {'status':'failed','error':'External interpretation could not complete.'}
    elif prefs.mode != 'local':
        result['consent'] = {'required':True,'message':'A local pattern explanation is available. Enable source sharing to request external interpretation. Detected sensitive values will be redacted first.'}
    # Keep the live response original, but mask detected credentials in durable history.
    saved_result = dict(result)
    saved_result['original_log'] = redacted
    saved_lines = redacted.splitlines()
    if redacted.endswith(('\n', '\r')): saved_lines.append('')
    saved_result['line_explanations'] = [
        {**row, 'original': saved_lines[index] if index < len(saved_lines) else row['original']}
        for index, row in enumerate(result['line_explanations'])
    ]
    session_id = request.data.get('session_id')
    if session_id:
        session = get_object_or_404(DebuggingSession, id=session_id, user=request.user)
        session.terminal_logs = redacted
        session.error_message = result['quick_summary']
        session.save(update_fields=['terminal_logs','error_message','updated_at'])
    else:
        session = DebuggingSession.objects.create(user=request.user, terminal_logs=redacted, error_message=result['quick_summary'], language='technical-log', status='ANALYZED')
    AnalysisResult.objects.create(session=session, diagnosis=json.dumps(saved_result, ensure_ascii=False), evidence_json={'source':result['source'],'classification':result['classification'],'technologies':result['technologies']})
    result['session_id'] = session.id
    return Response(result, status=status.HTTP_200_OK)
