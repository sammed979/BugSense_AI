import re
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.dashboard.models import DebuggingSession
from .models import ExerciseSubmission, LearningActivity, LearningProgress, LearningTopic, QuizAttempt

ERROR_CATEGORIES = tuple(value for value, _label in LearningTopic.CATEGORY_CHOICES)


def error_topics():
    """Return only the current debugging curriculum without deleting legacy records."""
    return LearningTopic.objects.filter(category__in=ERROR_CATEGORIES, error_name__gt='')


def topic_payload(topic, user, detail=False):
    progress = LearningProgress.objects.filter(user=user, topic=topic).first()
    payload = {
        'id':topic.id,'title':topic.title,'category':topic.category,'error_name':topic.error_name,
        'technology':topic.technology,'difficulty':topic.difficulty,'description':topic.description,
        'explanation':topic.explanation,'buggy_code':topic.buggy_code,'expected_error':topic.expected_error,
        'practice_question':topic.practice_question,
        'completed':bool(progress and progress.completed),'bookmarked':bool(progress and progress.bookmarked),
    }
    if detail:
        data = topic.lesson_data or {}
        payload['root_cause'] = data.get('root_cause', topic.description)
        payload['reproduce'] = data.get('reproduce', topic.buggy_code)
        payload['troubleshooting'] = data.get('troubleshooting', [topic.correction_explanation])
        payload['prevention'] = data.get('prevention', '')
        payload['challenge'] = data.get('challenge', topic.practice_question)
        payload['hints'] = data.get('hints', [])
        payload['line_explanations'] = data.get('line_explanations', [])
        payload['quiz'] = [{'question':q['question'],'options':q['options']} for q in data.get('quiz', [])]
    return payload


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def learning_topics(request):
    topics = error_topics()
    category = request.query_params.get('category','').strip()
    difficulty = request.query_params.get('difficulty','').strip()
    technology = request.query_params.get('technology','').strip()
    query = request.query_params.get('q','').strip()
    if category: topics = topics.filter(category=category)
    if difficulty in ('beginner','intermediate','advanced'): topics = topics.filter(difficulty=difficulty)
    if technology: topics = topics.filter(technology__icontains=technology)
    if query:
        topics = topics.filter(Q(title__icontains=query)|Q(error_name__icontains=query)|Q(category__icontains=query)|Q(technology__icontains=query)|Q(description__icontains=query)|Q(expected_error__icontains=query)|Q(keywords__icontains=query))
    return Response([topic_payload(topic,request.user) for topic in topics])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def learning_dashboard(request):
    topics = error_topics()
    progress = LearningProgress.objects.filter(user=request.user, topic__category__in=ERROR_CATEGORIES)
    submissions = ExerciseSubmission.objects.filter(user=request.user, topic__category__in=ERROR_CATEGORIES)
    quizzes = QuizAttempt.objects.filter(user=request.user, topic__category__in=ERROR_CATEGORIES)
    quiz_total = sum(item.total for item in quizzes)
    quiz_score = sum(item.score for item in quizzes)
    recent = progress.select_related('topic').order_by('-last_studied')[:5]
    recommended = topics.exclude(id__in=progress.filter(completed=True).values('topic_id')).first()
    return Response({
        'total_lessons':topics.count(),'completed_lessons':progress.filter(completed=True).count(),
        'challenges_attempted':submissions.count(),'challenges_solved':submissions.filter(solved=True).count(),
        'quiz_accuracy':round(100*quiz_score/quiz_total,1) if quiz_total else None,
        'progress_percent':round(100*progress.filter(completed=True).count()/topics.count(),1) if topics.exists() else 0,
        'recently_studied':[topic_payload(item.topic,request.user) for item in recent],
        'bookmarked':[topic_payload(item.topic,request.user) for item in progress.filter(bookmarked=True).select_related('topic')],
        'recommended_next':topic_payload(recommended,request.user) if recommended else None,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def learning_recommendations(request):
    evidence = ' '.join([request.query_params.get('error_type',''),request.query_params.get('message',''),request.query_params.get('technology','')]).strip()
    if not evidence: return Response({'recommendations':[]})
    words = [word.lower() for word in re.findall(r'[A-Za-z][A-Za-z0-9_]{2,}', evidence)]
    scored=[]
    for topic in error_topics():
        haystack=' '.join([topic.title,topic.error_name,topic.category,topic.technology,topic.description,*topic.keywords]).lower()
        score=sum(3 for word in words if word in haystack)
        if topic.error_name.lower() in evidence.lower(): score+=10
        if score: scored.append((score,topic))
    scored.sort(key=lambda item:(-item[0],item[1].order))
    return Response({'recommendations':[{'reason':f"Matches detected error information: {topic.error_name or topic.category}.",'lesson':topic_payload(topic,request.user)} for _,topic in scored[:4]]})


@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
def lesson_progress(request, topic_id):
    topic=get_object_or_404(error_topics(),id=topic_id)
    if request.method=='GET':
        LearningProgress.objects.get_or_create(user=request.user,topic=topic)
        return Response(topic_payload(topic,request.user,detail=True))
    completed=request.data.get('completed')
    bookmarked=request.data.get('bookmarked')
    if completed is not None and not isinstance(completed,bool): return Response({'error':'completed must be a boolean.'},status=400)
    if bookmarked is not None and not isinstance(bookmarked,bool): return Response({'error':'bookmarked must be a boolean.'},status=400)
    if completed is True and not (ExerciseSubmission.objects.filter(user=request.user,topic=topic,solved=True).exists() or QuizAttempt.objects.filter(user=request.user,topic=topic,score__gt=0).exists()):
        return Response({'error':'Complete a practice challenge or score a quiz point before marking this lesson complete.'},status=400)
    progress,_=LearningProgress.objects.get_or_create(user=request.user,topic=topic)
    fields=[]
    if completed is not None: progress.completed=completed; fields.append('completed')
    if bookmarked is not None: progress.bookmarked=bookmarked; fields.append('bookmarked')
    if fields: progress.save(update_fields=fields+['last_studied'])
    return Response(topic_payload(topic,request.user))


def _valid_answer(topic, root_cause, proposed_fix):
    if not root_cause.strip() or not proposed_fix.strip(): return False
    required=[term.lower() for term in (topic.lesson_data or {}).get('accepted_terms',[]) if len(term)>2]
    cause=root_cause.lower(); fix=proposed_fix.lower()
    error=(topic.error_name or '').lower()
    cause_rules={
        'nameerror':('name','scope','defined','variable'), 'typeerror':('type','value','operand','operation'),
        'valueerror':('value','conversion','format'), 'attributerror':('none','attribute','object'),
        'attributeerror':('none','attribute','object'), 'indexerror':('index','position','sequence'),
        'keyerror':('key','mapping','dictionary'), 'syntaxerror':('syntax','parse','parenthes','quote'),
        'missing table':('table','missing','exist'), 'http 401':('authenticat','token','credential'),
        'http 403':('permission','authoriz','access'), 'http 404':('route','resource','url','path'),
        'http 500':('server','traceback','exception','request'), 'http 429':('rate','quota','limit','retry'),
        'http 502':('gateway','upstream','proxy'), 'http 503':('service','unavailable','health'),
        'noreversematch':('route','name','argument','url'), 'template does not exist':('template','path','loader'),
        'csrf verification failed':('csrf','token','origin'), 'failed to fetch':('network','cors','fetch','preflight'),
        'referenceerror':('name','identifier','scope','declared'), 'integrityerror':('constraint','unique','duplicate'),
    }
    cause_terms=cause_rules.get(error, tuple(required))
    cause_ok=any(term in cause for term in cause_terms)
    fix_rules={
        'nameerror':('define','assign','import','spell','scope'), 'missing table':('migration','migrate','database','showmigrations','makemigrations'),
        'operationalerror / connection failure':('listen','host','port','connection','network'),
        'http 401':('token','bearer','sign','credential','refresh'), 'http 403':('permission','role','grant','policy'),
        'http 404':('route','url','path','host','method'), 'http 429':('wait','backoff','quota','limit','retry-after'),
        'http 502':('upstream','gateway','request id','proxy'), 'http 503':('health','retry-after','backoff','service'),
        'integrityerror':('duplicate','constraint','unique','validate','handle'),
    }
    fix_terms=fix_rules.get(error,('check','inspect','verify','validate','correct','configure','handle','test','use','add','change','find','compare','read','run','install','set','send','apply','review','trace','confirm','return','select','stop','serve'))
    return cause_ok and any(term in fix for term in fix_terms)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_exercise(request, topic_id):
    topic=get_object_or_404(error_topics(),id=topic_id)
    line=request.data.get('proposed_line',''); cause=request.data.get('root_cause',''); fix=request.data.get('proposed_fix','')
    difficulty=request.data.get('difficulty',topic.difficulty)
    hints=request.data.get('hints_revealed',0)
    if difficulty not in ('beginner','intermediate','advanced') or not all(isinstance(x,str) for x in (line,cause,fix)) or not isinstance(hints,int) or hints<0 or hints>len((topic.lesson_data or {}).get('hints',[])):
        return Response({'error':'Provide a valid exercise response.'},status=400)
    if any(len(x)>5000 for x in (line,cause,fix)): return Response({'error':'Exercise responses are limited to 5,000 characters.'},status=400)
    solved=_valid_answer(topic,cause,fix)
    submission=ExerciseSubmission.objects.create(user=request.user,topic=topic,difficulty=difficulty,proposed_line=line,root_cause=cause,proposed_fix=fix,hints_revealed=hints,solved=solved)
    if solved: LearningProgress.objects.update_or_create(user=request.user,topic=topic,defaults={'completed':True,'last_studied':timezone.now()})
    data=topic.lesson_data or {}
    # Explain the rubric after submission, whether or not the answer was accepted.
    return Response({'id':submission.id,'solved':solved,'feedback':'Your answer identifies the key evidence.' if solved else 'Not quite yet. Compare your response with the logged error and use a hint, then try again.','root_cause':data.get('root_cause',topic.description),'corrected_code':topic.corrected_code,'correction_explanation':topic.correction_explanation,'expected_concepts':data.get('accepted_terms',[]) if not solved else []},status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_quiz(request, topic_id):
    topic=get_object_or_404(error_topics(),id=topic_id)
    answers=request.data.get('answers')
    quiz=(topic.lesson_data or {}).get('quiz',[])
    if not isinstance(answers,list) or len(answers)!=len(quiz) or any(not isinstance(x,int) for x in answers): return Response({'error':'Submit one option index for each quiz question.'},status=400)
    score=sum(answer==question['correct_index'] for answer,question in zip(answers,quiz))
    attempt=QuizAttempt.objects.create(user=request.user,topic=topic,score=score,total=len(quiz),responses=answers)
    return Response({'id':attempt.id,'score':score,'total':len(quiz),'explanations':[{'correct':answer==question['correct_index'],'explanation':question['explanation']} for answer,question in zip(answers,quiz)]},status=201)


@api_view(['GET','POST'])
@permission_classes([IsAuthenticated])
def learning_activities(request):
    if request.method=='GET':
        items=LearningActivity.objects.filter(user=request.user)
        kind=request.query_params.get('type')
        if kind in ('practice','quiz','lesson'): items=items.filter(activity_type=kind)
        return Response([{'id':x.id,'type':x.activity_type,'prompt':x.prompt,'answer':x.answer,'completed':x.completed,'session_id':x.session_id,'created_at':x.created_at.isoformat()} for x in items[:100]])
    prompt=request.data.get('prompt',''); kind=request.data.get('type','lesson'); answer=request.data.get('answer',''); completed=request.data.get('completed') is True
    if kind not in ('practice','quiz','lesson') or not isinstance(prompt,str) or not prompt.strip() or len(prompt)>5000 or not isinstance(answer,str) or len(answer)>5000: return Response({'error':'Provide a valid learning activity.'},status=400)
    session=None
    if request.data.get('session_id'): session=get_object_or_404(DebuggingSession,id=request.data['session_id'],user=request.user)
    item=LearningActivity.objects.create(user=request.user,session=session,activity_type=kind,prompt=prompt.strip(),answer=answer,completed=completed)
    return Response({'id':item.id,'type':item.activity_type,'prompt':item.prompt,'answer':item.answer,'completed':item.completed,'session_id':item.session_id},status=201)
