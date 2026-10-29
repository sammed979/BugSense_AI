from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from apps.dashboard.models import Project
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
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Check for path traversal attacks
            for file_info in zip_ref.infolist():
                # Resolve the target path to prevent directory traversal
                resolved_path = (Path(temp_dir) / file_info.filename).resolve()
                # Ensure the resolved path is within the temp directory
                if not str(resolved_path).startswith(str(temp_dir)):
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
                        project_files.append(rel_path)
        
        # Create project
        project_name = uploaded_file.name.replace('.zip', '')
        project = Project.objects.create(
            user=request.user,
            name=project_name,
            source_type='upload',
            language='python'
        )
        
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
            {'error': f'Upload failed: {str(e)}'},
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
        })
    
    if request.method == 'DELETE':
        project.delete()
        return Response({'message': 'Project deleted successfully'})
