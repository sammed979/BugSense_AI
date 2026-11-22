"""
Code Analyzer - Static analysis using language-specific tools.

Supports Python (ast + ruff), Java/C/C++ (compiler diagnostics captured via the
sandbox runners), and JavaScript (node --check). Dispatches by detected language
so Java/C/C++/JS source is never sent to the Python parser.
"""
import ast
import builtins
import json
import re
import shutil
import subprocess
import symtable
from typing import List, Optional
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

    # ------------------------------------------------------------------
    # Multi-language analysis
    # ------------------------------------------------------------------

    @staticmethod
    def check_syntax_for_language(code: str, language: str) -> List[SyntaxErrorInfo]:
        """Run the language-appropriate syntax/compiler check."""
        if language == 'python':
            return CodeAnalyzer.check_syntax(code)
        if language == 'javascript':
            return CodeAnalyzer._check_javascript_syntax(code)
        if language == 'java':
            return CodeAnalyzer._check_compiled_language(code, 'java')
        if language == 'c':
            return CodeAnalyzer._check_compiled_language(code, 'c')
        if language == 'cpp':
            return CodeAnalyzer._check_compiled_language(code, 'cpp')
        return []

    @staticmethod
    def _check_javascript_syntax(code: str) -> List[SyntaxErrorInfo]:
        node = shutil.which('node')
        if not node:
            return []
        try:
            result = subprocess.run(
                [node, '--check', '-'],
                input=code,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (subprocess.SubprocessError, OSError):
            return []
        errors = []
        if result.returncode != 0 and result.stderr:
            # node --check output: file:line:col\nSyntaxError: message
            for line in result.stderr.splitlines():
                m = re.search(r':(\d+)(?::(\d+))?\s*$', line)
                if m:
                    line_no = int(m.group(1))
                    col = int(m.group(2)) if m.group(2) else 0
                    errors.append(SyntaxErrorInfo(line=line_no, column=col, message=line.strip()))
                    break
            if not errors:
                errors.append(SyntaxErrorInfo(line=0, column=0, message=result.stderr.strip().splitlines()[-1] if result.stderr.strip() else 'Syntax error'))
        return errors

    @staticmethod
    def _check_compiled_language(code: str, language: str) -> List[SyntaxErrorInfo]:
        """Compile the source and parse compiler error lines."""
        from sandbox.runners import get_runner
        runner = get_runner(language)
        if runner is None:
            return []
        try:
            exit_code, _stdout, stderr, _duration = runner.execute(code, timeout=10)
        except Exception:
            return []
        errors = []
        if exit_code != 0 and stderr:
            # gcc/g++/javac: file:line:col: error: message  OR  file:line: error: message
            for line in stderr.splitlines():
                m = re.search(r'[:.](\d+)(?::(\d+))?:\s*(?:error|fatal error|warning):\s*(.+)$', line)
                if m:
                    errors.append(SyntaxErrorInfo(
                        line=int(m.group(1)),
                        column=int(m.group(2)) if m.group(2) else 0,
                        message=m.group(3).strip(),
                    ))
                if len(errors) >= 10:
                    break
        return errors

    @staticmethod
    def analyze_error_context(code: str, error_message: str, language: str = 'python') -> dict:
        """Build a deterministic, source-aware diagnosis for the given language.

        Dispatches to the language-specific handler so Java/C/C++/JS source is
        never sent to the Python parser.
        """
        if language == 'python':
            return CodeAnalyzer._analyze_python(code, error_message)
        if language == 'javascript':
            return CodeAnalyzer._analyze_javascript(code, error_message)
        if language in ('java', 'c', 'cpp'):
            return CodeAnalyzer._analyze_compiled(code, error_message, language)
        return CodeAnalyzer._analyze_unknown(code, error_message, language)

    @staticmethod
    def _analyze_python(code: str, error_message: str) -> dict:
        """Existing Python diagnosis, kept verbatim."""
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
            'programming_language': 'python',
        }
        if error_category == 'NameError':
            diagnosis['undefined_variable'] = local.get('identifier')
        return diagnosis

    @staticmethod
    def _analyze_javascript(code: str, error_message: str) -> dict:
        error_text = error_message or ''
        syntax_errors = CodeAnalyzer._check_javascript_syntax(code)
        if not error_text.strip() or error_text.strip().lower() == 'no error message':
            if syntax_errors:
                error_text = syntax_errors[0].message
            else:
                return CodeAnalyzer._no_error_diagnosis('javascript')

        exception_type, exception_message = CodeAnalyzer._parse_js_error(error_text)
        line = CodeAnalyzer._extract_js_line(error_text) or (syntax_errors[0].line if syntax_errors else None)
        source_line = None
        if line and 1 <= line <= len(code.splitlines()):
            source_line = code.splitlines()[line - 1]

        category = exception_type or ('SyntaxError' if syntax_errors else 'JavaScriptError')
        return {
            'error_category': category,
            'exception_type': exception_type,
            'exception_message': exception_message,
            'programming_language': 'javascript',
            'summary': f'{category}: {exception_message}' if exception_message else category,
            'affected_file': None,
            'affected_line': line,
            'function_name': None,
            'failing_source_line': source_line,
            'possible_causes': [exception_message] if exception_message else [],
            'confirmed_findings': f'{category} raised at line {line}' if line else category,
            'root_cause': exception_message,
            'likely_root_cause': exception_message,
            'impact': 'The JavaScript program stopped at the failing statement.',
            'fix_steps': [f'Inspect line {line} and correct the {category}.' if line else f'Correct the {category}.'],
            'suggested_fix': None,
            'suggested_code': None,
            'why_fix_works': 'Fixing the reported statement allows the JavaScript engine to continue execution.',
            'prevention': 'Run node --check before executing, and validate variable/property access.',
            'frames': [],
            'secondary_errors': [],
            'confidence': 85,
            'detection_source': 'deterministic',
            'educational_explanation': None,
        }

    @staticmethod
    def _analyze_compiled(code: str, error_message: str, language: str) -> dict:
        error_text = error_message or ''
        syntax_errors = CodeAnalyzer._check_compiled_language(code, language)
        if not error_text.strip() or error_text.strip().lower() == 'no error message':
            if syntax_errors:
                error_text = syntax_errors[0].message
            else:
                return CodeAnalyzer._no_error_diagnosis(language)

        first = syntax_errors[0] if syntax_errors else None
        line = first.line if first else None
        source_line = None
        if line and 1 <= line <= len(code.splitlines()):
            source_line = code.splitlines()[line - 1]

        lang_label = {'java': 'Java', 'c': 'C', 'cpp': 'C++'}.get(language, language)
        category = f'{lang_label} Compilation Error' if syntax_errors else f'{lang_label} Runtime Error'
        return {
            'error_category': category,
            'exception_type': category,
            'exception_message': first.message if first else error_text.strip().splitlines()[-1] if error_text.strip() else '',
            'programming_language': language,
            'summary': f'{category}: {first.message}' if first else category,
            'affected_file': None,
            'affected_line': line,
            'function_name': None,
            'failing_source_line': source_line,
            'possible_causes': [e.message for e in syntax_errors] if syntax_errors else [error_text.strip()],
            'confirmed_findings': f'{lang_label} compiler reported an error at line {line}' if line else category,
            'root_cause': first.message if first else error_text.strip(),
            'likely_root_cause': first.message if first else error_text.strip(),
            'impact': f'The {lang_label} program could not be compiled/executed.',
            'fix_steps': [f'Review the compiler error at line {line} and fix the reported issue.' if line else 'Review the compiler errors and fix the reported issues.'],
            'suggested_fix': None,
            'suggested_code': None,
            'why_fix_works': f'Correcting the reported error lets the {lang_label} compiler produce a valid binary.',
            'prevention': f'Compile frequently and address warnings; use a {lang_label} linter in your editor.',
            'frames': [],
            'secondary_errors': [],
            'confidence': 85,
            'detection_source': 'deterministic',
            'educational_explanation': None,
        }

    @staticmethod
    def _no_error_diagnosis(language: str) -> dict:
        return {
            'error_category': 'Unknown',
            'programming_language': language,
            'summary': 'No runtime error was supplied; review the static findings below.',
            'possible_causes': [],
            'confidence': 0,
            'detection_source': 'static_only',
        }

    @staticmethod
    def _analyze_unknown(code: str, error_message: str, language: str) -> dict:
        """Fallback diagnosis for a language without a dedicated handler."""
        error_text = (error_message or '').strip()
        return {
            'error_category': 'Unknown',
            'programming_language': language,
            'summary': error_text or 'No specific error could be identified for this language.',
            'possible_causes': [error_text] if error_text else [],
            'confidence': 0,
            'detection_source': 'static_only',
        }

    @staticmethod
    def _parse_js_error(text: str) -> tuple:
        # ReferenceError: x is not defined\n    at ...
        m = re.search(r'^(?:\w+\.)?([A-Z][A-Za-z0-9_]*Error):\s*(.+)$', text, re.MULTILINE)
        if m:
            return m.group(1), m.group(2).strip()
        return None, text.strip().splitlines()[-1] if text.strip() else ''

    @staticmethod
    def _extract_js_line(text: str) -> Optional[int]:
        # at function (file.js:12:34)  or  file.js:12
        m = re.search(r':(\d+)(?::\d+)?\)?\s*$', text, re.MULTILINE)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                return None
        return None
