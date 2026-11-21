"""
Code Analyzer - Static analysis using Python AST and Ruff.
"""
import ast
import builtins
import json
import re
import symtable
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
        """Return referenced names that have no binding in their Python scope."""
        try:
            module = symtable.symtable(code, '<user-code>', 'exec')
        except (SyntaxError, ValueError):
            return []

        builtin_names = set(dir(builtins))
        module_bindings = {
            symbol.get_name() for symbol in module.get_symbols()
            if symbol.is_assigned() or symbol.is_imported() or symbol.is_namespace()
        }
        undefined = set()

        def visit(table, enclosing_bindings=frozenset(), module_scope=False):
            symbols = table.get_symbols()
            local_bindings = {
                symbol.get_name() for symbol in symbols
                if symbol.is_assigned() or symbol.is_parameter() or symbol.is_imported() or symbol.is_namespace()
            }
            visible_enclosing = set(enclosing_bindings)
            for symbol in symbols:
                name = symbol.get_name()
                if not symbol.is_referenced() or name in builtin_names or name.startswith('__'):
                    continue
                if module_scope:
                    if name not in module_bindings:
                        undefined.add(name)
                elif symbol.is_global():
                    if name not in module_bindings:
                        undefined.add(name)
                elif symbol.is_free() and name not in visible_enclosing:
                    undefined.add(name)

            for child in table.get_children():
                visit(child, visible_enclosing | local_bindings, False)

        visit(module, module_scope=True)
        return sorted(undefined)

    @staticmethod
    def analyze_error_context(code: str, error_message: str) -> dict:
        """Build a deterministic, source-aware diagnosis before optional AI."""
        from services.error_parser import ErrorParser
        from services.log_sense import explain_local

        error_text = error_message or ''
        if not error_text.strip() or error_text.strip().lower() == 'no error message':
            syntax_errors = CodeAnalyzer.check_syntax(code)
            if syntax_errors:
                error_text = f'SyntaxError: {syntax_errors[0].message}'
            else:
                return {
                    'error_category': 'Unknown',
                    'summary': 'No runtime error was supplied; review the static findings below.',
                    'possible_causes': [],
                    'confidence': 0,
                    'detection_source': 'static_only',
                }

        tracebacks = ErrorParser.parse_tracebacks(error_text)
        parsed = tracebacks[-1] if tracebacks else None
        direct_error = re.search(
            r'^\s*(?P<type>(?:[A-Za-z_]\w*\.)*[A-Z][A-Za-z0-9_]*):\s*(?P<message>.*)$',
            error_text,
            re.MULTILINE,
        )
        direct_exception_type = (
            direct_error.group('type').rsplit('.', 1)[-1]
            if direct_error else ErrorParser.extract_error_type(error_text)
        )
        local = explain_local(error_text, source_code=code)
        local_root = local.get('root_cause') or {}
        primary_frame = parsed.frames[-1] if parsed and parsed.frames else None
        source_line = (
            primary_frame.code_line
            if primary_frame and primary_frame.code_line
            else None
        )
        if primary_frame and not source_line and 1 <= primary_frame.line_number <= len(code.splitlines()):
            source_line = code.splitlines()[primary_frame.line_number - 1]

        recognized_local = local.get('status') == 'complete' and local.get('error_type') != 'Unknown / informational'
        if parsed and parsed.exception_type != 'UnknownError':
            error_category = parsed.exception_type
            summary = local.get('quick_summary') or f'{parsed.exception_type}: {parsed.exception_message}'
            confidence = int((local_root.get('confidence') or 0.8) * 100)
        elif recognized_local:
            error_category = (
                direct_exception_type
                or (local.get('error_type') or 'Detected technical error').removeprefix('Python ')
            )
            summary = local.get('quick_summary') or 'A known error signature was detected.'
            confidence = int((local_root.get('confidence') or 0.75) * 100)
        else:
            return {
                'error_category': 'Unknown',
                'summary': local.get('quick_summary') or 'No specific runtime error could be identified.',
                'possible_causes': [],
                'confidence': 25,
                'detection_source': 'local_patterns',
                'what_happened': local.get('what_happened'),
                'why_happened': local_root.get('uncertainty'),
                'impact': local.get('impact'),
                'prevention': local.get('prevention'),
            }

        frames = [
            {
                'file_path': frame.file_path,
                'line_number': frame.line_number,
                'function_name': frame.function_name,
                'code_line': frame.code_line,
            }
            for frame in parsed.frames
        ] if parsed else []
        causes = []
        if local_root.get('confirmed'):
            causes.append(local_root['confirmed'])
        causes.extend(
            item.get('cause', item) if isinstance(item, dict) else item
            for item in local_root.get('possible', [])
        )
        diagnosis = {
            'error_category': error_category,
            'exception_type': parsed.exception_type if parsed else direct_exception_type or local.get('exception_type'),
            'exception_message': parsed.exception_message if parsed else direct_error.group('message').strip() if direct_error else '',
            'summary': summary,
            'affected_file': primary_frame.file_path if primary_frame else None,
            'affected_line': primary_frame.line_number if primary_frame else None,
            'function_name': primary_frame.function_name if primary_frame else None,
            'failing_source_line': source_line,
            'possible_causes': causes,
            'confirmed_findings': local_root.get('confirmed'),
            'root_cause': local_root.get('confirmed'),
            'likely_root_cause': local_root.get('likely'),
            'impact': local.get('impact') or 'The failure stops the current operation; broader application impact is not established by this input alone.',
            'fix_steps': local.get('fix_steps', []),
            'suggested_fix': (local.get('fix_steps') or [None])[0],
            'suggested_code': local.get('correct_example'),
            'why_fix_works': local.get('why_fix_works'),
            'prevention': local.get('prevention'),
            'frames': frames,
            'secondary_errors': [
                {
                    'exception_type': item.exception_type,
                    'exception_message': item.exception_message,
                    'is_final': index == len(tracebacks) - 1,
                    'is_secondary': bool(item.preceding_relation),
                    'relationship': item.preceding_relation,
                }
                for index, item in enumerate(tracebacks)
            ],
            'confidence': confidence,
            'detection_source': 'deterministic',
            'educational_explanation': local.get('educational_explanation'),
        }
        if error_category == 'NameError':
            diagnosis['undefined_variable'] = local.get('identifier')
        return diagnosis

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
                timeout=3,
                encoding='utf-8',
                errors='replace'
            )

            if result.stdout:
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
