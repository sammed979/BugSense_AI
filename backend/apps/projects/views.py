from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from apps.dashboard.models import Project, ProjectFile
import os
import zipfile
import tempfile
import shutil
from pathlib import Path


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
    """Upload a ZIP archive containing project files."""
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
    
    # Validate file size (max 10MB)
    max_size = 10 * 1024 * 1024
    if uploaded_file.size > max_size:
        return Response(
            {'error': 'File size exceeds 10MB limit'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create temporary directory for extraction
    temp_dir = tempfile.mkdtemp(prefix='bugsense_upload_')
    
    try:
        # Save uploaded file
        zip_path = os.path.join(temp_dir, 'upload.zip')
        with open(zip_path, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)
        
        # Extract ZIP safely
        project_files = []
        text_files = []
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Check for path traversal attacks
            for file_info in zip_ref.infolist():
                # Resolve the target path to prevent directory traversal
                resolved_path = (Path(temp_dir) / file_info.filename).resolve()
                # Ensure the resolved path is within the temp directory
                try:
                    resolved_path.relative_to(Path(temp_dir).resolve())
                except ValueError:
                    return Response(
                        {'error': 'Invalid file path detected (possible path traversal)'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Extract files
            zip_ref.extractall(temp_dir)
            
            # List extracted files
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, temp_dir)
                    # Skip the zip file itself
                    if rel_path != 'upload.zip':
                        if Path(file_path).stat().st_size <= 1_000_000:
                            try:
                                content = Path(file_path).read_text(encoding='utf-8')
                            except (UnicodeDecodeError, OSError):
                                continue
                            normalized_path = rel_path.replace('\\', '/')
                            text_files.append(ProjectFile(path=normalized_path, content=content))
                            project_files.append(normalized_path)
        
        # Create project
        project_name = uploaded_file.name.replace('.zip', '')
        project = Project.objects.create(
            user=request.user,
            name=project_name,
            source_type='upload',
            language='python'
        )
        for item in text_files:
            item.project = project
        ProjectFile.objects.bulk_create(text_files)
        
        return Response({
            'id': project.id,
            'name': project.name,
            'source_type': project.source_type,
            'language': project.language,
            'files': project_files,
            'file_count': len(project_files),
            'created_at': project.created_at.isoformat(),
        }, status=status.HTTP_201_CREATED)
    
    except zipfile.BadZipFile:
        return Response(
            {'error': 'Invalid ZIP file'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            {'error': 'Project upload could not be completed. Check that the ZIP contains valid files.'},
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
