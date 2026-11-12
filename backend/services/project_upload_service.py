"""
Secure project upload service with ZIP extraction and validation.
Handles single files, multiple files, and ZIP archives with security checks.
"""

import os
import zipfile
import hashlib
import mimetypes
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime


class ProjectUploadConfig:
    """Configuration for project upload security limits."""

    # File size limits
    MAX_SINGLE_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    MAX_TOTAL_EXTRACTED_SIZE = 100 * 1024 * 1024  # 100 MB
    MAX_ARCHIVE_SIZE = 50 * 1024 * 1024  # 50 MB

    # File count limits
    MAX_FILES_PER_UPLOAD = 500
    MAX_ARCHIVE_NESTING_DEPTH = 5

    # Allowed file extensions
    ALLOWED_EXTENSIONS = {
        # Programming languages
        '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.c', '.cpp', '.h', '.cs', '.php',
        # Web
        '.html', '.css', '.scss', '.sass', '.less',
        # Config and data
        '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
        # Documentation
        '.md', '.txt', '.rst',
        # SQL
        '.sql',
        # Other safe text files
        '.sh', '.bat', '.ps1', '.rb', '.go', '.rs', '.swift', '.kt',
    }

    # Binary extensions to reject
    BINARY_EXTENSIONS = {
        '.exe', '.dll', '.so', '.dylib', '.bin', '.o', '.a', '.lib',
        '.zip', '.tar', '.gz', '.bz2', '.7z', '.rar',
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.svg',
        '.mp3', '.mp4', '.avi', '.mov', '.pdf', '.doc', '.docx', '.xls', '.xlsx',
    }

    # Dangerous filenames patterns
    DANGEROUS_PATTERNS = [
        '..',  # Path traversal
        '~',   # Backup files
        '.DS_Store',
        'Thumbs.db',
    ]


class FileValidationError(Exception):
    """Raised when file validation fails."""
    pass


class ZipExtractionError(Exception):
    """Raised when ZIP extraction fails."""
    pass


class ProjectUploadService:
    """Service for secure project file upload and extraction."""

    def __init__(self, workspace_base_dir: str):
        """
        Initialize the upload service.

        Args:
            workspace_base_dir: Base directory for project workspaces
        """
        self.workspace_base_dir = Path(workspace_base_dir)
        self.workspace_base_dir.mkdir(parents=True, exist_ok=True)

    def validate_file_extension(self, filename: str) -> bool:
        """
        Validate file extension.

        Args:
            filename: Name of the file to validate

        Returns:
            True if extension is allowed, False otherwise
        """
        ext = Path(filename).suffix.lower()
        return ext in ProjectUploadConfig.ALLOWED_EXTENSIONS

    def is_binary_file(self, filename: str) -> bool:
        """
        Check if file is binary based on extension.

        Args:
            filename: Name of the file to check

        Returns:
            True if file appears to be binary
        """
        ext = Path(filename).suffix.lower()
        return ext in ProjectUploadConfig.BINARY_EXTENSIONS

    def validate_filename(self, filename: str) -> bool:
        """
        Validate filename for security issues.

        Args:
            filename: Name of the file to validate

        Returns:
            True if filename is safe, False otherwise
        """
        # Check for path traversal
        if '..' in filename or filename.startswith('/'):
            return False

        # Check for dangerous patterns
        for pattern in ProjectUploadConfig.DANGEROUS_PATTERNS:
            if pattern in filename:
                return False

        # Check length
        if len(filename) > 255:
            return False

        return True

    def validate_file_size(self, size: int) -> bool:
        """
        Validate file size.

        Args:
            size: File size in bytes

        Returns:
            True if size is within limits
        """
        return size <= ProjectUploadConfig.MAX_SINGLE_FILE_SIZE

    def calculate_file_hash(self, content: bytes) -> str:
        """
        Calculate SHA-256 hash of file content.

        Args:
            content: File content as bytes

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(content).hexdigest()

    def extract_zip(
        self,
        zip_path: str,
        destination_dir: str,
        max_files: int = None,
        max_size: int = None
    ) -> Tuple[List[Dict], int, int]:
        """
        Securely extract ZIP archive with security checks.

        Args:
            zip_path: Path to ZIP file
            destination_dir: Directory to extract to
            max_files: Maximum number of files to extract (optional)
            max_size: Maximum total size to extract (optional)

        Returns:
            Tuple of (list of extracted file info, total files extracted, total size)

        Raises:
            ZipExtractionError: If extraction fails or security check fails
        """
        if max_files is None:
            max_files = ProjectUploadConfig.MAX_FILES_PER_UPLOAD
        if max_size is None:
            max_size = ProjectUploadConfig.MAX_TOTAL_EXTRACTED_SIZE

        destination = Path(destination_dir)
        destination.mkdir(parents=True, exist_ok=True)

        extracted_files = []
        total_size = 0
        file_count = 0

        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Check for ZIP bomb
                if len(zip_ref.namelist()) > max_files:
                    raise ZipExtractionError(
                        f"ZIP contains too many files: {len(zip_ref.namelist())} > {max_files}"
                    )

                # Check total uncompressed size
                total_uncompressed = sum(f.file_size for f in zip_ref.infolist())
                if total_uncompressed > max_size:
                    raise ZipExtractionError(
                        f"ZIP total size too large: {total_uncompressed} > {max_size}"
                    )

                for file_info in zip_ref.infolist():
                    # Skip directories
                    if file_info.is_dir():
                        continue

                    filename = file_info.filename

                    # Validate filename
                    if not self.validate_filename(filename):
                        raise ZipExtractionError(f"Invalid filename in ZIP: {filename}")

                    # Check for nested archives
                    if self.is_binary_file(filename):
                        continue  # Skip binary files

                    # Validate extension
                    if not self.validate_file_extension(filename):
                        continue  # Skip unsupported files

                    # Check individual file size
                    if file_info.file_size > ProjectUploadConfig.MAX_SINGLE_FILE_SIZE:
                        raise ZipExtractionError(
                            f"File too large in ZIP: {filename} ({file_info.file_size} bytes)"
                        )

                    # Extract file
                    target_path = destination / filename
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                    with zip_ref.open(file_info) as source:
                        content = source.read()

                        # Validate it's actually text (basic check)
                        try:
                            content.decode('utf-8')
                        except UnicodeDecodeError:
                            continue  # Skip binary content

                        target_path.write_bytes(content)

                    extracted_files.append({
                        'path': filename,
                        'size': file_info.file_size,
                        'hash': self.calculate_file_hash(content),
                    })

                    total_size += file_info.file_size
                    file_count += 1

                    if file_count >= max_files:
                        break

        except zipfile.BadZipFile as e:
            raise ZipExtractionError(f"Invalid ZIP file: {str(e)}")
        except Exception as e:
            raise ZipExtractionError(f"ZIP extraction error: {str(e)}")

        return extracted_files, file_count, total_size

    def process_single_file(
        self,
        file_path: str,
        relative_path: str = None
    ) -> Dict:
        """
        Process a single uploaded file.

        Args:
            file_path: Path to uploaded file
            relative_path: Relative path within project (optional)

        Returns:
            Dictionary with file information

        Raises:
            FileValidationError: If validation fails
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileValidationError(f"File does not exist: {file_path}")

        # Validate filename
        filename = file_path.name
        if not self.validate_filename(filename):
            raise FileValidationError(f"Invalid filename: {filename}")

        # Validate extension
        if not self.validate_file_extension(filename):
            raise FileValidationError(f"Unsupported file extension: {filename}")

        # Check size
        size = file_path.stat().st_size
        if not self.validate_file_size(size):
            raise FileValidationError(f"File too large: {filename} ({size} bytes)")

        # Check if binary
        if self.is_binary_file(filename):
            raise FileValidationError(f"Binary file not allowed: {filename}")

        # Read and validate content
        try:
            content = file_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            raise FileValidationError(f"File is not valid UTF-8 text: {filename}")

        # Use provided relative path or filename
        path = relative_path if relative_path else filename

        return {
            'path': path,
            'content': content,
            'size': size,
            'hash': self.calculate_file_hash(content.encode('utf-8')),
        }

    def create_project_workspace(self, project_id: int) -> Path:
        """
        Create a workspace directory for a project.

        Args:
            project_id: Project ID

        Returns:
            Path to workspace directory
        """
        workspace_dir = self.workspace_base_dir / f"project_{project_id}"
        workspace_dir.mkdir(parents=True, exist_ok=True)
        return workspace_dir

    def cleanup_workspace(self, project_id: int) -> bool:
        """
        Remove a project workspace directory.

        Args:
            project_id: Project ID

        Returns:
            True if cleanup successful
        """
        workspace_dir = self.workspace_base_dir / f"project_{project_id}"
        if workspace_dir.exists():
            import shutil
            shutil.rmtree(workspace_dir)
            return True
        return False
