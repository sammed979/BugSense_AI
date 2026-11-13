from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from django.conf import settings
from django.utils import timezone
from apps.dashboard.models import Project, ProjectFile, ProjectAnalysis, ProjectIssue, SuggestedFix, AppliedChange
from apps.projects.serializers import ProjectSerializer, ProjectFileSerializer, ProjectAnalysisSerializer, ProjectIssueSerializer
import os
import zipfile
import tempfile
import shutil
from pathlib import Path
from services.project_upload_service import ProjectUploadService, FileValidationError, ZipExtractionError
from services.project_discovery_service import ProjectDiscoveryService
from services.static_analysis_service import StaticAnalysisService
from services.project_ai_service import ProjectAIService
from services.analysis_cache import get_analysis_cache


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def project_list(request):
    """List or create projects."""
    if request.method == 'GET':
        projects = Project.objects.filter(user=request.user).order_by('-created_at')
        return Response({
            'projects': [
                {
                    'id': p.id,
                    'name': p.name,
                    'source_type': p.source_type,
                    'language': p.language,
                    'created_at': p.created_at.isoformat(),
                    'file_count': p.files.count(),
                }
                for p in projects
            ]
        })
    
    if request.method == 'POST':
        name = request.data.get('name')
        source_type = request.data.get('source_type', 'upload')
        language = request.data.get('language', 'python')
        
        if not name:
            return Response(
                {'error': 'name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        project = Project.objects.create(
            user=request.user,
            name=name,
            source_type=source_type,
            language=language
        )
        
        return Response({
            'id': project.id,
            'name': project.name,
            'source_type': project.source_type,
            'language': project.language,
            'created_at': project.created_at.isoformat(),
        }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_project(request):
    """Upload a ZIP archive containing project files using secure extraction."""
    if 'file' not in request.FILES:
        return Response(
            {'error': 'No file provided'},
            status=status.HTTP_400_BAD_REQUEST
        )

    uploaded_file = request.FILES['file']

    # Validate file type
    if not uploaded_file.name.endswith('.zip'):
        return Response(
            {'error': 'Only ZIP files are supported'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Create temporary directory for extraction
    temp_dir = tempfile.mkdtemp(prefix='bugsense_upload_')
    zip_path = os.path.join(temp_dir, 'upload.zip')

    try:
        # Save uploaded file
        with open(zip_path, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        # Initialize secure upload service
        workspace_base = os.path.join(settings.MEDIA_ROOT, 'project_workspaces')
        upload_service = ProjectUploadService(workspace_base)

        # Extract ZIP securely
        extracted_files, file_count, total_size = upload_service.extract_zip(
            zip_path,
            temp_dir
        )

        if file_count == 0:
            return Response(
                {'error': 'No valid text files found in ZIP'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create project
        project_name = uploaded_file.name.replace('.zip', '')
        project = Project.objects.create(
            user=request.user,
            name=project_name,
            source_type='upload',
            language='python'  # Will be updated by discovery
        )

        # Create workspace
        workspace_dir = upload_service.create_project_workspace(project.id)

        # Copy extracted files to workspace and store in database
        project_files = []
        for file_info in extracted_files:
            source_path = Path(temp_dir) / file_info['path']
            workspace_path = workspace_dir / file_info['path']
            workspace_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, workspace_path)

            # Store in database
            try:
                content = source_path.read_text(encoding='utf-8')
                project_file = ProjectFile.objects.create(
                    project=project,
                    path=file_info['path'],
                    content=content
                )
                project_files.append(file_info['path'])
            except Exception:
                continue

        # Run project discovery
        discovery_service = ProjectDiscoveryService(str(workspace_dir))
        analysis = discovery_service.scan_project()

        # Update project with discovered information
        if analysis.get('languages'):
            project.language = analysis['languages'][0] if analysis['languages'] else 'python'
            project.save()

        # Create initial project analysis record
        project_analysis = ProjectAnalysis.objects.create(
            project=project,
            analysis_type='static',
            status='completed',
            total_files=analysis.get('total_files', 0),
            analyzed_files=analysis.get('total_files', 0),
            summary={
                'languages': analysis.get('languages', []),
                'frameworks': analysis.get('frameworks', []),
                'file_counts': analysis.get('file_counts', {}),
                'file_categories': {k: len(v) for k, v in analysis.get('file_categories', {}).items()},
            }
        )

        return Response({
            'id': project.id,
            'name': project.name,
            'source_type': project.source_type,
            'language': project.language,
            'files': project_files,
            'file_count': len(project_files),
            'analysis': {
                'languages': analysis.get('languages', []),
                'frameworks': analysis.get('frameworks', []),
                'total_files': analysis.get('total_files', 0),
                'file_counts': analysis.get('file_counts', {}),
            },
            'created_at': project.created_at.isoformat(),
        }, status=status.HTTP_201_CREATED)

    except ZipExtractionError as e:
        return Response(
            {'error': f'ZIP extraction error: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': f'Project upload failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    finally:
        # Clean up temporary directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def project_detail(request, project_id):
    """Retrieve or delete a project."""
    try:
        project = Project.objects.get(id=project_id, user=request.user)
    except Project.DoesNotExist:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        return Response({
            'id': project.id,
            'name': project.name,
            'source_type': project.source_type,
            'language': project.language,
            'created_at': project.created_at.isoformat(),
            'updated_at': project.updated_at.isoformat(),
            'files': list(project.files.values('path', 'updated_at')),
        })
    
    if request.method == 'DELETE':
        project.delete()
        return Response({'message': 'Project deleted successfully'})


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def project_files(request, project_id):
    try:
        project = Project.objects.get(id=project_id, user=request.user)
    except Project.DoesNotExist:
        return Response({'error': 'Project not found'}, status=404)
    if request.method == 'GET':
        files = project.files.all()[:200]
        return Response({'files': [{'path': item.path, 'content': item.content, 'updated_at': item.updated_at.isoformat()} for item in files]})
    path = request.data.get('path')
    content = request.data.get('content')
    if not isinstance(path, str) or not path or len(path) > 512 or not isinstance(content, str) or len(content.encode('utf-8')) > 1_000_000:
        return Response({'error': 'Provide a project file path and text content under 1 MB.'}, status=400)
    normalized = Path(path.replace('\\', '/'))
    if normalized.is_absolute() or '..' in normalized.parts:
        return Response({'error': 'Invalid project file path.'}, status=400)
    item, _created = ProjectFile.objects.update_or_create(project=project, path=normalized.as_posix(), defaults={'content': content})
    return Response({'path': item.path, 'updated_at': item.updated_at.isoformat()})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_single_file(request):
    """Upload a single source file to a project."""
    project_id = request.data.get('project_id')
    if 'file' not in request.FILES:
        return Response(
            {'error': 'No file provided'},
            status=status.HTTP_400_BAD_REQUEST
        )

    uploaded_file = request.FILES['file']

    try:
        if project_id:
            project = Project.objects.get(id=project_id, user=request.user)
        else:
            # Create new project
            project_name = Path(uploaded_file.name).stem
            project = Project.objects.create(
                user=request.user,
                name=project_name,
                source_type='upload',
                language='python'
            )

        # Initialize upload service
        workspace_base = os.path.join(settings.MEDIA_ROOT, 'project_workspaces')
        upload_service = ProjectUploadService(workspace_base)

        # Create workspace if needed
        workspace_dir = upload_service.create_project_workspace(project.id)

        # Process file
        temp_path = os.path.join(tempfile.gettempdir(), uploaded_file.name)
        with open(temp_path, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        try:
            file_info = upload_service.process_single_file(temp_path, uploaded_file.name)

            # Save to workspace
            workspace_path = workspace_dir / file_info['path']
            workspace_path.parent.mkdir(parents=True, exist_ok=True)
            workspace_path.write_text(file_info['content'], encoding='utf-8')

            # Store in database
            project_file, created = ProjectFile.objects.update_or_create(
                project=project,
                path=file_info['path'],
                defaults={'content': file_info['content']}
            )

            return Response({
                'id': project.id,
                'name': project.name,
                'file': {
                    'path': project_file.path,
                    'size': file_info['size'],
                },
                'created': created,
            }, status=status.HTTP_201_CREATED)

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Project.DoesNotExist:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except FileValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': f'File upload failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_multiple_files(request):
    """Upload multiple source files to a project."""
    project_id = request.data.get('project_id')

    if 'files' not in request.FILES:
        return Response(
            {'error': 'No files provided'},
            status=status.HTTP_400_BAD_REQUEST
        )

    uploaded_files = request.FILES.getlist('files')

    try:
        if project_id:
            project = Project.objects.get(id=project_id, user=request.user)
        else:
            # Create new project
            project = Project.objects.create(
                user=request.user,
                name='Uploaded Project',
                source_type='upload',
                language='python'
            )

        # Initialize upload service
        workspace_base = os.path.join(settings.MEDIA_ROOT, 'project_workspaces')
        upload_service = ProjectUploadService(workspace_base)
        workspace_dir = upload_service.create_project_workspace(project.id)

        uploaded = []
        errors = []

        for uploaded_file in uploaded_files:
            temp_path = os.path.join(tempfile.gettempdir(), f"temp_{uploaded_file.name}")
            try:
                with open(temp_path, 'wb') as f:
                    for chunk in uploaded_file.chunks():
                        f.write(chunk)

                file_info = upload_service.process_single_file(temp_path, uploaded_file.name)

                # Save to workspace
                workspace_path = workspace_dir / file_info['path']
                workspace_path.parent.mkdir(parents=True, exist_ok=True)
                workspace_path.write_text(file_info['content'], encoding='utf-8')

                # Store in database
                project_file, created = ProjectFile.objects.update_or_create(
                    project=project,
                    path=file_info['path'],
                    defaults={'content': file_info['content']}
                )

                uploaded.append({
                    'path': project_file.path,
                    'size': file_info['size'],
                    'created': created,
                })

            except FileValidationError as e:
                errors.append({'file': uploaded_file.name, 'error': str(e)})
            except Exception as e:
                errors.append({'file': uploaded_file.name, 'error': str(e)})
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        return Response({
            'id': project.id,
            'name': project.name,
            'uploaded': uploaded,
            'errors': errors,
            'total_uploaded': len(uploaded),
            'total_errors': len(errors),
        })

    except Project.DoesNotExist:
        return Response(
            {'error': 'Project not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Multiple file upload failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_analysis(request, project_id):
    """Get project analysis results."""
    try:
        project = Project.objects.get(id=project_id, user=request.user)
    except Project.DoesNotExist:
        return Response({'error': 'Project not found'}, status=404)

    analyses = project.analyses.all().order_by('-created_at')
    return Response({
        'analyses': [ProjectAnalysisSerializer(a).data for a in analyses]
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def project_issues(request, project_id):
    """Get issues found in project analysis."""
    try:
        project = Project.objects.get(id=project_id, user=request.user)
    except Project.DoesNotExist:
        return Response({'error': 'Project not found'}, status=404)

    # Get latest analysis
    latest_analysis = project.analyses.first()
    if not latest_analysis:
        return Response({'issues': []})

    issues = latest_analysis.issues.all()
    return Response({
        'issues': [ProjectIssueSerializer(i).data for i in issues]
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def run_static_analysis(request, project_id):
    """Run static analysis on a project."""
    try:
        project = Project.objects.get(id=project_id, user=request.user)
    except Project.DoesNotExist:
        return Response({'error': 'Project not found'}, status=404)

    # Get all project files
    project_files = project.files.all()
    files_dict = {pf.path: pf.content for pf in project_files}

    if not files_dict:
        return Response(
            {'error': 'No files to analyze'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check cache
    cache_key = f"static_analysis_{project_id}_{len(files_dict)}"
    cache = get_analysis_cache()
    cached_result = cache.get(cache_key)

    if cached_result and not request.data.get('force_refresh', False):
        return Response({
            'analysis_id': cached_result['analysis_id'],
            'total_issues': cached_result['total_issues'],
            'issues_by_severity': cached_result['issues_by_severity'],
            'issues_by_category': cached_result['issues_by_category'],
            'analyzed_files': len(files_dict),
            'cached': True,
        })

    # Run static analysis
    analyzer = StaticAnalysisService(files_dict)
    analysis_result = analyzer.analyze_project()

    # Create analysis record
    project_analysis = ProjectAnalysis.objects.create(
        project=project,
        analysis_type='static',
        status='completed',
        total_files=len(files_dict),
        analyzed_files=len(files_dict),
        summary={
            'total_issues': analysis_result['total_issues'],
            'issues_by_severity': analysis_result['issues_by_severity'],
            'issues_by_category': analysis_result['issues_by_category'],
        }
    )

    # Create issue records
    issues_created = 0
    for file_path, issues in analysis_result['file_analyses'].items():
        for issue in issues:
            ProjectIssue.objects.create(
                analysis=project_analysis,
                issue_id=f"{project_id}_{file_path}_{issue.get('line_number', 0)}_{issues_created}",
                severity=issue.get('severity', 'medium'),
                category=issue.get('category', 'unknown'),
                affected_file=issue.get('affected_file', file_path),
                line_number=issue.get('line_number'),
                explanation=issue.get('explanation', ''),
                supporting_evidence=[],
                related_files=[],
                suggested_solution=issue.get('explanation', ''),  # For now, use explanation as solution
                confidence=issue.get('confidence', 50),
            )
            issues_created += 1

    # Add cross-file issues
    for issue in analysis_result['cross_file_issues']:
        ProjectIssue.objects.create(
            analysis=project_analysis,
            issue_id=f"{project_id}_crossfile_{issues_created}",
            severity=issue.get('severity', 'medium'),
            category=issue.get('category', 'unknown'),
            affected_file=issue.get('affected_file', ''),
            explanation=issue.get('explanation', ''),
            supporting_evidence=[],
            related_files=[],
            suggested_solution=issue.get('explanation', ''),
            confidence=issue.get('confidence', 50),
        )
        issues_created += 1

    # Cache the result
    cache.set(cache_key, {
        'analysis_id': project_analysis.id,
        'total_issues': analysis_result['total_issues'],
        'issues_by_severity': analysis_result['issues_by_severity'],
        'issues_by_category': analysis_result['issues_by_category'],
    }, ttl=1800)  # 30 minutes

    return Response({
        'analysis_id': project_analysis.id,
        'total_issues': analysis_result['total_issues'],
        'issues_by_severity': analysis_result['issues_by_severity'],
        'issues_by_category': analysis_result['issues_by_category'],
        'analyzed_files': len(files_dict),
        'cached': False,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_project(request, project_id):
    """Run complete project analysis (static + AI if available)."""
    try:
        project = Project.objects.get(id=project_id, user=request.user)
    except Project.DoesNotExist:
        return Response({'error': 'Project not found'}, status=404)

    # Get all project files
    project_files = project.files.all()
    files_dict = {pf.path: pf.content for pf in project_files}

    if not files_dict:
        return Response(
            {'error': 'No files to analyze'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Run static analysis
    analyzer = StaticAnalysisService(files_dict)
    analysis_result = analyzer.analyze_project()

    # Create analysis record
    project_analysis = ProjectAnalysis.objects.create(
        project=project,
        analysis_type='static',
        status='completed',
        total_files=len(files_dict),
        analyzed_files=len(files_dict),
        summary={
            'total_issues': analysis_result['total_issues'],
            'issues_by_severity': analysis_result['issues_by_severity'],
            'issues_by_category': analysis_result['issues_by_category'],
        }
    )

    # Create issue records
    issues_created = 0
    for file_path, issues in analysis_result['file_analyses'].items():
        for issue in issues:
            ProjectIssue.objects.create(
                analysis=project_analysis,
                issue_id=f"{project_id}_{file_path}_{issue.get('line_number', 0)}_{issues_created}",
                severity=issue.get('severity', 'medium'),
                category=issue.get('category', 'unknown'),
                affected_file=issue.get('affected_file', file_path),
                line_number=issue.get('line_number'),
                explanation=issue.get('explanation', ''),
                supporting_evidence=[],
                related_files=[],
                suggested_solution=issue.get('explanation', ''),
                confidence=issue.get('confidence', 50),
            )
            issues_created += 1

    return Response({
        'analysis_id': project_analysis.id,
        'issues_count': analysis_result['total_issues'],
        'issues_by_severity': analysis_result['issues_by_severity'],
        'issues_by_category': analysis_result['issues_by_category'],
        'analyzed_files': len(files_dict),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def run_ai_analysis(request, project_id):
    """Run AI analysis on project issues."""
    try:
        project = Project.objects.get(id=project_id, user=request.user)
    except Project.DoesNotExist:
        return Response({'error': 'Project not found'}, status=404)

    # Get latest static analysis
    latest_analysis = project.analyses.filter(analysis_type='static').first()
    if not latest_analysis:
        return Response(
            {'error': 'No static analysis found. Run static analysis first.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Get all project files
    project_files = project.files.all()
    files_dict = {pf.path: pf.content for pf in project_files}

    # Get static issues
    static_issues = latest_analysis.issues.all()
    static_issues_data = [ProjectIssueSerializer(i).data for i in static_issues]

    # Get project context from discovery
    workspace_base = os.path.join(settings.MEDIA_ROOT, 'project_workspaces')
    workspace_dir = os.path.join(workspace_base, f"project_{project_id}")

    discovery_service = ProjectDiscoveryService(workspace_dir)
    discovery_result = discovery_service.scan_project()

    project_context = {
        'languages': discovery_result.get('languages', []),
        'frameworks': discovery_result.get('frameworks', []),
        'total_files': discovery_result.get('total_files', 0),
    }

    # Get AI provider from user settings
    from apps.accounts.models import AIProviderSettings
    provider_settings = AIProviderSettings.objects.filter(user=request.user).first()
    provider = provider_settings.primary_provider if provider_settings else 'openai'

    # Run AI analysis
    ai_service = ProjectAIService()
    enhanced_issues = ai_service.analyze_project_with_ai(
        project_id=project_id,
        files=files_dict,
        static_issues=static_issues_data,
        project_context=project_context,
        provider=provider,
        max_issues=request.data.get('max_issues', 10)
    )

    # Create AI analysis record
    ai_analysis = ProjectAnalysis.objects.create(
        project=project,
        analysis_type='ai',
        status='completed',
        total_files=len(files_dict),
        analyzed_files=len(enhanced_issues),
        summary={
            'total_issues': len(enhanced_issues),
            'ai_provider': provider,
        }
    )

    # Update or create issue records with AI analysis
    for issue_data in enhanced_issues:
        # Check if issue already exists
        existing_issue = latest_analysis.issues.filter(
            affected_file=issue_data.get('affected_file'),
            line_number=issue_data.get('line_number')
        ).first()

        if existing_issue:
            # Update with AI insights
            existing_issue.ai_explanation = issue_data.get('ai_explanation', '')
            existing_issue.ai_root_cause = issue_data.get('ai_root_cause', '')
            existing_issue.ai_suggested_solution = issue_data.get('ai_suggested_solution', '')
            existing_issue.ai_confidence = issue_data.get('ai_confidence', 0)
            existing_issue.save()
        else:
            # Create new issue
            ProjectIssue.objects.create(
                analysis=ai_analysis,
                issue_id=f"{project_id}_ai_{issue_data.get('affected_file', '')}_{issue_data.get('line_number', 0)}",
                severity=issue_data.get('severity', 'medium'),
                category=issue_data.get('category', 'unknown'),
                affected_file=issue_data.get('affected_file', ''),
                line_number=issue_data.get('line_number'),
                explanation=issue_data.get('explanation', ''),
                supporting_evidence=issue_data.get('supporting_evidence', []),
                related_files=issue_data.get('related_files', []),
                root_cause=issue_data.get('ai_root_cause', ''),
                suggested_solution=issue_data.get('ai_suggested_solution', ''),
                confidence=issue_data.get('ai_confidence', 0),
            )

    return Response({
        'analysis_id': ai_analysis.id,
        'total_issues': len(enhanced_issues),
        'ai_provider': provider,
        'analyzed_files': len(enhanced_issues),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_repair(request, project_id):
    """Generate a repair suggestion for a specific issue."""
    try:
        project = Project.objects.get(id=project_id, user=request.user)
    except Project.DoesNotExist:
        return Response({'error': 'Project not found'}, status=404)

    issue_id = request.data.get('issue_id')
    if not issue_id:
        return Response({'error': 'issue_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Get the issue
    try:
        issue = ProjectIssue.objects.get(issue_id=issue_id)
    except ProjectIssue.DoesNotExist:
        return Response({'error': 'Issue not found'}, status=status.HTTP_404_NOT_FOUND)

    # Get the file content
    try:
        project_file = project.files.get(path=issue.affected_file)
    except ProjectFile.DoesNotExist:
        return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)

    # Get project context
    workspace_base = os.path.join(settings.MEDIA_ROOT, 'project_workspaces')
    workspace_dir = os.path.join(workspace_base, f"project_{project_id}")

    discovery_service = ProjectDiscoveryService(workspace_dir)
    discovery_result = discovery_service.scan_project()

    project_context = {
        'languages': discovery_result.get('languages', []),
        'frameworks': discovery_result.get('frameworks', []),
    }

    # Get AI provider
    from apps.accounts.models import AIProviderSettings
    provider_settings = AIProviderSettings.objects.filter(user=request.user).first()
    provider = provider_settings.primary_provider if provider_settings else 'openai'

    # Generate repair suggestion
    ai_service = ProjectAIService()
    repair_suggestion = ai_service.generate_repair_suggestion(
        issue=ProjectIssueSerializer(issue).data,
        file_content=project_file.content,
        project_context=project_context,
        provider=provider
    )

    # Create SuggestedFix record
    suggested_fix = SuggestedFix.objects.create(
        issue=issue,
        original_code=repair_suggestion['original_code'],
        suggested_code=repair_suggestion['suggested_code'],
        explanation=repair_suggestion['explanation'],
        diff_text=repair_suggestion['diff'],
        requires_approval=True,
        status='pending'
    )

    return Response({
        'fix_id': suggested_fix.id,
        'original_code': repair_suggestion['original_code'],
        'suggested_code': repair_suggestion['suggested_code'],
        'explanation': repair_suggestion['explanation'],
        'diff': repair_suggestion['diff'],
        'provider': repair_suggestion['provider'],
        'confidence': repair_suggestion['confidence'],
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_repair(request, project_id):
    """Apply an approved repair to the project workspace."""
    try:
        project = Project.objects.get(id=project_id, user=request.user)
    except Project.DoesNotExist:
        return Response({'error': 'Project not found'}, status=404)

    fix_id = request.data.get('fix_id')
    if not fix_id:
        return Response({'error': 'fix_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Get the suggested fix
    try:
        suggested_fix = SuggestedFix.objects.get(id=fix_id)
    except SuggestedFix.DoesNotExist:
        return Response({'error': 'Suggested fix not found'}, status=status.HTTP_404_NOT_FOUND)

    # Get the file
    file_path = suggested_fix.issue.affected_file
    try:
        project_file = project.files.get(path=file_path)
    except ProjectFile.DoesNotExist:
        return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)

    # Calculate hashes
    import hashlib
    original_hash = hashlib.sha256(project_file.content.encode('utf-8')).hexdigest()
    new_hash = hashlib.sha256(suggested_fix.suggested_code.encode('utf-8')).hexdigest()

    # Update the file in database
    project_file.content = suggested_fix.suggested_code
    project_file.save()

    # Update the file in workspace
    workspace_base = os.path.join(settings.MEDIA_ROOT, 'project_workspaces')
    workspace_dir = os.path.join(workspace_base, f"project_{project_id}")
    workspace_file_path = workspace_dir / file_path
    workspace_file_path.parent.mkdir(parents=True, exist_ok=True)
    workspace_file_path.write_text(suggested_fix.suggested_code, encoding='utf-8')

    # Update suggested fix status
    suggested_fix.status = 'applied'
    suggested_fix.approved_at = timezone.now()
    suggested_fix.applied_at = timezone.now()
    suggested_fix.save()

    # Create AppliedChange record
    from django.utils import timezone
    import uuid
    change_id = str(uuid.uuid4())
    applied_change = AppliedChange.objects.create(
        project=project,
        issue=suggested_fix.issue,
        file_path=file_path,
        original_hash=original_hash,
        new_hash=new_hash,
        diff_text=suggested_fix.diff_text,
        change_id=change_id,
        reason=suggested_fix.explanation,
        related_error_id=suggested_fix.issue.issue_id,
        approved=True,
        approved_at=timezone.now(),
        applied_at=timezone.now(),
    )

    return Response({
        'change_id': change_id,
        'file_path': file_path,
        'original_hash': original_hash,
        'new_hash': new_hash,
        'applied_at': applied_change.applied_at.isoformat(),
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_repair(request, project_id):
    """Reject a suggested repair."""
    try:
        project = Project.objects.get(id=project_id, user=request.user)
    except Project.DoesNotExist:
        return Response({'error': 'Project not found'}, status=404)

    fix_id = request.data.get('fix_id')
    if not fix_id:
        return Response({'error': 'fix_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Get and update the suggested fix
    try:
        suggested_fix = SuggestedFix.objects.get(id=fix_id)
        suggested_fix.status = 'rejected'
        suggested_fix.save()
    except SuggestedFix.DoesNotExist:
        return Response({'error': 'Suggested fix not found'}, status=status.HTTP_404_NOT_FOUND)

    return Response({'message': 'Repair rejected successfully'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rollback_change(request, project_id):
    """Rollback an applied change."""
    try:
        project = Project.objects.get(id=project_id, user=request.user)
    except Project.DoesNotExist:
        return Response({'error': 'Project not found'}, status=404)

    change_id = request.data.get('change_id')
    if not change_id:
        return Response({'error': 'change_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Get the applied change
    try:
        applied_change = AppliedChange.objects.get(change_id=change_id, project=project)
    except AppliedChange.DoesNotExist:
        return Response({'error': 'Change not found'}, status=status.HTTP_404_NOT_FOUND)

    # Get the file
    file_path = applied_change.file_path
    try:
        project_file = project.files.get(path=file_path)
    except ProjectFile.DoesNotExist:
        return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)

    # Restore original content from SuggestedFix if available
    try:
        suggested_fix = SuggestedFix.objects.filter(
            issue=applied_change.issue,
            status='applied'
        ).first()
        
        if suggested_fix and suggested_fix.original_code:
            # Restore to database
            project_file.content = suggested_fix.original_code
            project_file.save()
            
            # Restore to workspace
            workspace_base = os.path.join(settings.MEDIA_ROOT, 'project_workspaces')
            workspace_dir = os.path.join(workspace_base, f"project_{project_id}")
            workspace_file_path = workspace_dir / file_path
            workspace_file_path.parent.mkdir(parents=True, exist_ok=True)
            workspace_file_path.write_text(suggested_fix.original_code, encoding='utf-8')
            
            from django.utils import timezone
            applied_change.rolled_back_at = timezone.now()
            applied_change.save()
            
            return Response({
                'message': 'Change rolled back successfully',
                'rolled_back_at': applied_change.rolled_back_at.isoformat(),
                'file_path': file_path,
            })
        else:
            return Response({'error': 'Original content not available for rollback'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': f'Rollback failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_project(request, project_id):
    """Download the project as a ZIP archive."""
    try:
        project = Project.objects.get(id=project_id, user=request.user)
    except Project.DoesNotExist:
        return Response({'error': 'Project not found'}, status=404)

    # Create ZIP from workspace
    workspace_base = os.path.join(settings.MEDIA_ROOT, 'project_workspaces')
    workspace_dir = os.path.join(workspace_base, f"project_{project_id}")

    if not os.path.exists(workspace_dir):
        return Response({'error': 'Project workspace not found'}, status=status.HTTP_404_NOT_FOUND)

    # Create ZIP in memory
    import zipfile
    from django.http import HttpResponse
    from io import BytesIO

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(workspace_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, workspace_dir)
                zip_file.write(file_path, arc_path)

    zip_buffer.seek(0)

    response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{project.name}_repaired.zip"'
    return response
