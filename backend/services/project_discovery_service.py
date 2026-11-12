"""
Project file discovery and analysis service.
Identifies languages, frameworks, entry points, and file relationships.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Set, Optional
from collections import defaultdict


class LanguageDetector:
    """Detects programming languages from file extensions and content."""

    LANGUAGE_MAP = {
        # Python
        '.py': 'python',
        # JavaScript/TypeScript
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        # Java
        '.java': 'java',
        # C/C++
        '.c': 'c',
        '.cpp': 'cpp',
        '.h': 'c',
        '.hpp': 'cpp',
        # C#
        '.cs': 'csharp',
        # PHP
        '.php': 'php',
        # Web
        '.html': 'html',
        '.htm': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.sass': 'sass',
        '.less': 'less',
        # Config
        '.json': 'json',
        '.xml': 'xml',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.toml': 'toml',
        '.ini': 'ini',
        # SQL
        '.sql': 'sql',
        # Documentation
        '.md': 'markdown',
        '.rst': 'rst',
        # Other
        '.sh': 'shell',
        '.bash': 'shell',
        '.bat': 'batch',
        '.ps1': 'powershell',
        '.rb': 'ruby',
        '.go': 'go',
        '.rs': 'rust',
        '.swift': 'swift',
        '.kt': 'kotlin',
    }

    @classmethod
    def detect_from_extension(cls, filepath: str) -> Optional[str]:
        """Detect language from file extension."""
        ext = Path(filepath).suffix.lower()
        return cls.LANGUAGE_MAP.get(ext)

    @classmethod
    def detect_from_content(cls, content: str, filepath: str) -> Optional[str]:
        """Detect language from content (shebang, etc.)."""
        lines = content.split('\n')[:5]  # Check first 5 lines

        for line in lines:
            line = line.strip()
            if line.startswith('#!'):
                if 'python' in line:
                    return 'python'
                elif 'bash' in line or 'sh' in line:
                    return 'shell'
                elif 'node' in line:
                    return 'javascript'
                elif 'ruby' in line:
                    return 'ruby'
                elif 'php' in line:
                    return 'php'

        # Fall back to extension detection
        return cls.detect_from_extension(filepath)


class FrameworkDetector:
    """Detects frameworks from file structure and content."""

    DJANGO_INDICATORS = [
        'manage.py',
        'settings.py',
        'urls.py',
        'wsgi.py',
        'asgi.py',
    ]

    FLASK_INDICATORS = [
        'app.py',
        'wsgi.py',
        'requirements.txt',
    ]

    REACT_INDICATORS = [
        'package.json',
        'src/App.js',
        'src/App.jsx',
        'src/App.tsx',
        'public/index.html',
    ]

    VUE_INDICATORS = [
        'package.json',
        'src/App.vue',
        'src/main.js',
        'public/index.html',
    ]

    ANGULAR_INDICATORS = [
        'package.json',
        'angular.json',
        'src/main.ts',
        'src/app/app.module.ts',
    ]

    DJANGO_REST_INDICATORS = [
        'serializers.py',
        'views.py with rest_framework',
    ]

    @classmethod
    def detect_framework(cls, files: List[str], contents: Dict[str, str]) -> List[str]:
        """Detect frameworks from project files."""
        frameworks = []
        file_set = set(files)

        # Check Django
        if any(indicator in file_set for indicator in cls.DJANGO_INDICATORS):
            frameworks.append('Django')
            # Check Django REST
            for content in contents.values():
                if 'rest_framework' in content:
                    frameworks.append('Django REST Framework')
                    break

        # Check Flask
        if any(indicator in file_set for indicator in cls.FLASK_INDICATORS):
            frameworks.append('Flask')

        # Check React
        if any(indicator in file_set for indicator in cls.REACT_INDICATORS):
            frameworks.append('React')

        # Check Vue
        if any(indicator in file_set for indicator in cls.VUE_INDICATORS):
            frameworks.append('Vue.js')

        # Check Angular
        if any(indicator in file_set for indicator in cls.ANGULAR_INDICATORS):
            frameworks.append('Angular')

        return frameworks


class FileCategory:
    """File categories for organization."""

    SOURCE = 'source'
    CONFIG = 'config'
    DEPENDENCY = 'dependency'
    TEMPLATE = 'template'
    TEST = 'test'
    DOCUMENTATION = 'documentation'
    ASSET = 'asset'
    BUILD = 'build'
    UNKNOWN = 'unknown'

    @classmethod
    def categorize(cls, filepath: str, content: str = None) -> str:
        """Categorize a file based on path and content."""
        path = Path(filepath)
        name = path.name.lower()
        ext = path.suffix.lower()

        # Config files
        if name in ['settings.py', 'config.py', 'config.js', 'config.json', '.env', '.env.example']:
            return cls.CONFIG
        if ext in ['.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf']:
            return cls.CONFIG

        # Dependency files
        if name in ['requirements.txt', 'package.json', 'package-lock.json', 'yarn.lock', 'pom.xml', 'build.gradle']:
            return cls.DEPENDENCY
        if name in ['gemfile', 'cargo.toml', 'go.mod']:
            return cls.DEPENDENCY

        # Test files
        if 'test' in name or 'spec' in name:
            return cls.TEST
        if path.parent.name.lower() in ['tests', 'test', '__tests__', 'spec']:
            return cls.TEST

        # Template files
        if path.parent.name.lower() in ['templates', 'template']:
            return cls.TEMPLATE
        if ext in ['.html', '.htm'] and 'template' in str(path).lower():
            return cls.TEMPLATE

        # Documentation
        if ext in ['.md', '.rst', '.txt']:
            return cls.DOCUMENTATION
        if path.parent.name.lower() in ['docs', 'doc', 'documentation']:
            return cls.DOCUMENTATION

        # Build files
        if path.parent.name.lower() in ['build', 'dist', 'out', '.next', '.nuxt']:
            return cls.BUILD
        if name in ['webpack.config.js', 'tsconfig.json', 'babel.config.js']:
            return cls.BUILD

        # Assets
        if ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.css', '.scss', '.sass', '.less']:
            return cls.ASSET

        # Source files (default for code files)
        if ext in ['.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.c', '.cpp', '.h', '.cs', '.php', '.rb', '.go', '.rs']:
            return cls.SOURCE

        return cls.UNKNOWN


class PythonImportAnalyzer:
    """Analyzes Python imports to find dependencies."""

    IMPORT_PATTERNS = [
        re.compile(r'^from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import'),
        re.compile(r'^import\s+([a-zA-Z_][a-zA-Z0-9_,\s]*)'),
    ]

    @classmethod
    def extract_imports(cls, content: str) -> Set[str]:
        """Extract import statements from Python code."""
        imports = set()
        lines = content.split('\n')

        for line in lines:
            line = line.strip()
            for pattern in cls.IMPORT_PATTERNS:
                match = pattern.match(line)
                if match:
                    module = match.group(1).split(',')[0].strip()
                    imports.add(module)
                    break

        return imports


class JavaScriptImportAnalyzer:
    """Analyzes JavaScript/TypeScript imports."""

    IMPORT_PATTERNS = [
        re.compile(r'import\s+.*\s+from\s+[\'"]([^\'"]+)[\'"]'),
        re.compile(r'require\([\'"]([^\'"]+)[\'"]\)'),
    ]

    @classmethod
    def extract_imports(cls, content: str) -> Set[str]:
        """Extract import statements from JavaScript/TypeScript code."""
        imports = set()
        lines = content.split('\n')

        for line in lines:
            line = line.strip()
            for pattern in cls.IMPORT_PATTERNS:
                match = pattern.search(line)
                if match:
                    module = match.group(1)
                    imports.add(module)
                    break

        return imports


class ProjectDiscoveryService:
    """Service for discovering and analyzing project structure."""

    def __init__(self, workspace_dir: str):
        """
        Initialize the discovery service.

        Args:
            workspace_dir: Path to project workspace directory
        """
        self.workspace_dir = Path(workspace_dir)

    def scan_project(self) -> Dict:
        """
        Scan project directory and return comprehensive analysis.

        Returns:
            Dictionary with project analysis results
        """
        if not self.workspace_dir.exists():
            return {
                'error': 'Workspace directory does not exist',
                'files': [],
                'languages': [],
                'frameworks': [],
                'total_files': 0,
            }

        files = self._collect_files()
        contents = self._read_file_contents(files)

        analysis = {
            'files': files,
            'languages': self._detect_languages(files, contents),
            'frameworks': self._detect_frameworks(files, contents),
            'file_categories': self._categorize_files(files, contents),
            'imports': self._analyze_imports(files, contents),
            'total_files': len(files),
            'file_counts': self._count_by_language(files),
        }

        return analysis

    def _collect_files(self) -> List[str]:
        """Collect all file paths relative to workspace."""
        files = []
        for filepath in self.workspace_dir.rglob('*'):
            if filepath.is_file():
                # Get relative path
                rel_path = filepath.relative_to(self.workspace_dir)
                files.append(str(rel_path))
        return sorted(files)

    def _read_file_contents(self, files: List[str]) -> Dict[str, str]:
        """Read contents of text files."""
        contents = {}
        for filepath in files:
            full_path = self.workspace_dir / filepath
            try:
                content = full_path.read_text(encoding='utf-8', errors='ignore')
                contents[filepath] = content
            except Exception:
                contents[filepath] = ''
        return contents

    def _detect_languages(self, files: List[str], contents: Dict[str, str]) -> List[str]:
        """Detect programming languages used in project."""
        languages = set()
        for filepath in files:
            lang = LanguageDetector.detect_from_extension(filepath)
            if lang:
                languages.add(lang)
            else:
                # Try content detection
                content = contents.get(filepath, '')
                lang = LanguageDetector.detect_from_content(content, filepath)
                if lang:
                    languages.add(lang)
        return sorted(list(languages))

    def _detect_frameworks(self, files: List[str], contents: Dict[str, str]) -> List[str]:
        """Detect frameworks used in project."""
        return FrameworkDetector.detect_framework(files, contents)

    def _categorize_files(self, files: List[str], contents: Dict[str, str]) -> Dict[str, List[str]]:
        """Categorize files by type."""
        categories = defaultdict(list)
        for filepath in files:
            content = contents.get(filepath, '')
            category = FileCategory.categorize(filepath, content)
            categories[category].append(filepath)
        return dict(categories)

    def _analyze_imports(self, files: List[str], contents: Dict[str, str]) -> Dict[str, Set[str]]:
        """Analyze imports in source files."""
        imports = {}
        for filepath in files:
            content = contents.get(filepath, '')
            ext = Path(filepath).suffix.lower()

            if ext == '.py':
                imports[filepath] = PythonImportAnalyzer.extract_imports(content)
            elif ext in ['.js', '.jsx', '.ts', '.tsx']:
                imports[filepath] = JavaScriptImportAnalyzer.extract_imports(content)

        return imports

    def _count_by_language(self, files: List[str]) -> Dict[str, int]:
        """Count files by language."""
        counts = defaultdict(int)
        for filepath in files:
            lang = LanguageDetector.detect_from_extension(filepath)
            if lang:
                counts[lang] += 1
            else:
                counts['other'] += 1
        return dict(counts)

    def get_entry_points(self, files: List[str], contents: Dict[str, str]) -> List[str]:
        """Identify likely entry points for the project."""
        entry_points = []

        # Common entry point patterns
        entry_patterns = [
            'main.py',
            'app.py',
            'index.js',
            'index.ts',
            'index.tsx',
            'index.html',
            'manage.py',
            'server.js',
            'app.js',
        ]

        for filepath in files:
            name = Path(filepath).name.lower()
            if name in entry_patterns:
                entry_points.append(filepath)

        return entry_points

    def get_configuration_files(self, files: List[str]) -> List[str]:
        """Get configuration files."""
        config_files = []
        for filepath in files:
            category = FileCategory.categorize(filepath)
            if category == FileCategory.CONFIG:
                config_files.append(filepath)
        return config_files

    def get_dependency_files(self, files: List[str]) -> List[str]:
        """Get dependency files."""
        dep_files = []
        for filepath in files:
            category = FileCategory.categorize(filepath)
            if category == FileCategory.DEPENDENCY:
                dep_files.append(filepath)
        return dep_files
