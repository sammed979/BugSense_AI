"""
Project-level static analysis service.
Detects syntax errors, undefined references, missing imports, and other issues.
"""

import ast
import re
from pathlib import Path
from typing import List, Dict, Set, Optional
from collections import defaultdict


class PythonStaticAnalyzer:
    """Static analysis for Python code using AST."""

    def __init__(self, file_path: str, content: str):
        """
        Initialize analyzer.

        Args:
            file_path: Path to the file being analyzed
            content: File content
        """
        self.file_path = file_path
        self.content = content
        self.issues = []
        self.imports = set()
        self.defined_names = set()
        self.undefined_names = set()

    def analyze(self) -> List[Dict]:
        """
        Perform static analysis on Python code.

        Returns:
            List of detected issues
        """
        try:
            tree = ast.parse(self.content, filename=self.file_path)
        except SyntaxError as e:
            return [{
                'severity': 'critical',
                'category': 'syntax_error',
                'affected_file': self.file_path,
                'line_number': e.lineno,
                'explanation': f'Syntax error: {e.msg}',
                'confidence': 100,
            }]

        # Collect imports and definitions
        self._collect_symbols(tree)

        # Check for undefined names
        self._check_undefined_names(tree)

        # Check for unused imports
        self._check_unused_imports()

        return self.issues

    def _collect_symbols(self, tree: ast.AST):
        """Collect imports and defined names."""
        for node in ast.walk(tree):
            # Collect imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.imports.add(node.module.split('.')[0])
                for alias in node.names:
                    self.imports.add(alias.name)

            # Collect defined names
            if isinstance(node, ast.FunctionDef):
                self.defined_names.add(node.name)
            elif isinstance(node, ast.AsyncFunctionDef):
                self.defined_names.add(node.name)
            elif isinstance(node, ast.ClassDef):
                self.defined_names.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.defined_names.add(target.id)
            elif isinstance(node, ast.AnnAssign):
                if isinstance(target := node.target, ast.Name):
                    self.defined_names.add(target.id)

    def _check_undefined_names(self, tree: ast.AST):
        """Check for undefined variable references."""
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                if node.id not in self.defined_names and node.id not in self.imports:
                    # Skip builtins
                    if node.id not in __builtins__:
                        self.undefined_names.add(node.id)
                        self.issues.append({
                            'severity': 'high',
                            'category': 'undefined_reference',
                            'affected_file': self.file_path,
                            'line_number': getattr(node, 'lineno', None),
                            'explanation': f'Undefined reference: {node.id}',
                            'confidence': 80,
                        })

    def _check_unused_imports(self):
        """Check for unused imports."""
        for imp in self.imports:
            if imp not in self.defined_names and imp not in self.content:
                self.issues.append({
                    'severity': 'low',
                    'category': 'unused_import',
                    'affected_file': self.file_path,
                    'explanation': f'Unused import: {imp}',
                    'confidence': 90,
                })


class JavaScriptStaticAnalyzer:
    """Basic static analysis for JavaScript/TypeScript."""

    def __init__(self, file_path: str, content: str):
        """
        Initialize analyzer.

        Args:
            file_path: Path to the file being analyzed
            content: File content
        """
        self.file_path = file_path
        self.content = content
        self.issues = []

    def analyze(self) -> List[Dict]:
        """
        Perform basic static analysis on JavaScript/TypeScript code.

        Returns:
            List of detected issues
        """
        # Check for common syntax issues
        issues = []

        # Check for console.log statements (debugging code)
        if 'console.log' in self.content:
            issues.append({
                'severity': 'low',
                'category': 'debugging_code',
                'affected_file': self.file_path,
                'explanation': 'console.log statement found (debugging code)',
                'confidence': 95,
            })

        # Check for TODO comments
        if 'TODO' in self.content or 'FIXME' in self.content:
            issues.append({
                'severity': 'informational',
                'category': 'todo_comment',
                'affected_file': self.file_path,
                'explanation': 'TODO/FIXME comment found',
                'confidence': 100,
            })

        # Check for var usage (should use let/const)
        if re.search(r'\bvar\s+', self.content):
            issues.append({
                'severity': 'low',
                'category': 'deprecated_syntax',
                'affected_file': self.file_path,
                'explanation': 'var keyword used (prefer let/const)',
                'confidence': 90,
            })

        return issues


class CrossFileAnalyzer:
    """Analyzes cross-file dependencies and inconsistencies."""

    def __init__(self, files: Dict[str, str]):
        """
        Initialize cross-file analyzer.

        Args:
            files: Dictionary mapping file paths to content
        """
        self.files = files
        self.issues = []

    def analyze(self) -> List[Dict]:
        """
        Perform cross-file analysis.

        Returns:
            List of cross-file issues
        """
        # Check for Django-specific patterns
        self._check_django_patterns()

        # Check for missing referenced files
        self._check_missing_references()

        return self.issues

    def _check_django_patterns(self):
        """Check for Django-specific cross-file issues."""
        # Collect models
        models = {}
        for path, content in self.files.items():
            if path.endswith('models.py'):
                # Extract model class names
                class_pattern = r'class\s+(\w+)\s*\(.*models\.Model'
                for match in re.finditer(class_pattern, content):
                    models[match.group(1)] = path

        # Check views for model references
        for path, content in self.files.items():
            if path.endswith('views.py'):
                for model_name, model_path in models.items():
                    if model_name in content:
                        # Check if the corresponding import exists
                        import_pattern = f'from.*{Path(model_path).stem}.*import.*{model_name}'
                        if not re.search(import_pattern, content):
                            self.issues.append({
                                'severity': 'medium',
                                'category': 'missing_import',
                                'affected_file': path,
                                'explanation': f'Possible missing import for model {model_name} from {model_path}',
                                'confidence': 70,
                            })

    def _check_missing_references(self):
        """Check for references to files that don't exist."""
        # Check Python imports
        for path, content in self.files.items():
            if path.endswith('.py'):
                # Extract import statements
                import_pattern = r'from\s+([^\s]+)\s+import|import\s+([^\s,]+)'
                for match in re.finditer(import_pattern, content):
                    module = match.group(1) or match.group(2)
                    # Convert module path to potential file path
                    module_path = module.replace('.', '/') + '.py'
                    if module_path not in self.files and not module.startswith('.'):
                        # Might be external library, so mark as informational
                        self.issues.append({
                            'severity': 'informational',
                            'category': 'external_dependency',
                            'affected_file': path,
                            'explanation': f'Import of external module: {module}',
                            'confidence': 50,
                        })


class StaticAnalysisService:
    """Service for project-wide static analysis."""

    def __init__(self, files: Dict[str, str]):
        """
        Initialize static analysis service.

        Args:
            files: Dictionary mapping file paths to content
        """
        self.files = files

    def analyze_project(self) -> Dict:
        """
        Perform project-wide static analysis.

        Returns:
            Dictionary with analysis results
        """
        all_issues = []
        file_analyses = {}

        # Analyze each file
        for file_path, content in self.files.items():
            issues = self._analyze_file(file_path, content)
            all_issues.extend(issues)
            file_analyses[file_path] = issues

        # Perform cross-file analysis
        cross_file_analyzer = CrossFileAnalyzer(self.files)
        cross_file_issues = cross_file_analyzer.analyze()
        all_issues.extend(cross_file_issues)

        # Categorize issues
        issue_summary = self._summarize_issues(all_issues)

        return {
            'total_issues': len(all_issues),
            'issues_by_severity': issue_summary['by_severity'],
            'issues_by_category': issue_summary['by_category'],
            'file_analyses': file_analyses,
            'cross_file_issues': cross_file_issues,
        }

    def _analyze_file(self, file_path: str, content: str) -> List[Dict]:
        """Analyze a single file based on its language."""
        ext = Path(file_path).suffix.lower()

        if ext == '.py':
            analyzer = PythonStaticAnalyzer(file_path, content)
            return analyzer.analyze()
        elif ext in ['.js', '.jsx', '.ts', '.tsx']:
            analyzer = JavaScriptStaticAnalyzer(file_path, content)
            return analyzer.analyze()
        else:
            return []

    def _summarize_issues(self, issues: List[Dict]) -> Dict:
        """Summarize issues by severity and category."""
        by_severity = defaultdict(int)
        by_category = defaultdict(int)

        for issue in issues:
            by_severity[issue.get('severity', 'unknown')] += 1
            by_category[issue.get('category', 'unknown')] += 1

        return {
            'by_severity': dict(by_severity),
            'by_category': dict(by_category),
        }
