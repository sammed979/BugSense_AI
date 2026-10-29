"""
Code Analyzer - Static analysis using Python AST and Ruff.
"""
import ast
import subprocess
from typing import List
from dataclasses import dataclass


@dataclass
class SyntaxErrorInfo:
    line: int
    column: int
    message: str


@dataclass
class LintIssue:
    code: str
    message: str
    line: int
    column: int
    severity: str


class CodeAnalyzer:
    """Perform static analysis on Python code."""

    @staticmethod
    def check_syntax(code: str) -> List[SyntaxErrorInfo]:
        """Check Python code for syntax errors."""
        errors = []
        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(SyntaxErrorInfo(
                line=e.lineno or 0,
                column=e.offset or 0,
                message=str(e)
            ))
        return errors

    @staticmethod
    def extract_undefined_names(code: str) -> List[str]:
        """Extract potentially undefined names from code using AST."""
        undefined = []
        defined = set()
        builtins = set(__builtins__.keys()) if hasattr(__builtins__, 'keys') else set(dir(__builtins__))

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return undefined

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                defined.add(node.id)
            elif isinstance(node, ast.FunctionDef):
                defined.add(node.name)
            elif isinstance(node, ast.ClassDef):
                defined.add(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    defined.add(alias.asname or alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    defined.add(alias.asname or alias.name)

        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                if node.id not in defined and node.id not in builtins and not node.id.startswith('__'):
                    undefined.append(node.id)

        return list(set(undefined))

    @staticmethod
    def run_ruff(code: str) -> List[LintIssue]:
        """Run Ruff linter on code if available."""
        issues = []
        try:
            result = subprocess.run(
                ['ruff', 'check', '--format', 'json', '-'],
                input=code,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.stdout:
                import json
                ruff_output = json.loads(result.stdout)
                for item in ruff_output:
                    issues.append(LintIssue(
                        code=item.get('code', 'UNK'),
                        message=item.get('message', ''),
                        line=item.get('location', {}).get('row', 0),
                        column=item.get('location', {}).get('column', 0),
                        severity='error' if item.get('fix', {}).get('applicability') == 'unsafe' else 'warning'
                    ))
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass

        return issues
