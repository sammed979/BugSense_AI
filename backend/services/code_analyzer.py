"""
Code Analyzer - Static analysis using Python AST and Ruff.
"""
import ast
import builtins
import json
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
        """Analyze error context to provide better diagnosis."""
        diagnosis = {
            'error_category': 'Unknown',
            'summary': 'No analysis available',
            'possible_causes': [],
            'confidence': 0
        }
        
        # Determine error type from message
        if 'NameError' in error_message:
            diagnosis['error_category'] = 'NameError'
            diagnosis['summary'] = 'A variable is used before being defined'
            diagnosis['possible_causes'] = ['Variable not defined', 'Typo in variable name', 'Variable defined in different scope']
            diagnosis['confidence'] = 80
            
            # Extract undefined variable
            import re
            match = re.search(r"name '(\w+)' is not defined", error_message)
            if match:
                var_name = match.group(1)
                diagnosis['undefined_variable'] = var_name
                
                # Check if there's a function that could compute this
                function_names = []
                try:
                    tree = ast.parse(code)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            function_names.append(node.name)
                except:
                    pass
                
                if function_names:
                    diagnosis['available_functions'] = function_names
                    
        elif 'ZeroDivisionError' in error_message:
            diagnosis['error_category'] = 'ZeroDivisionError'
            diagnosis['summary'] = 'Division by zero occurred'
            diagnosis['possible_causes'] = ['Divisor is zero', 'Missing zero check before division']
            diagnosis['confidence'] = 90
            
        elif 'TypeError' in error_message:
            diagnosis['error_category'] = 'TypeError'
            diagnosis['summary'] = 'Operation applied to incompatible type'
            diagnosis['possible_causes'] = ['Wrong data type', 'Missing type conversion', 'Incorrect operation for type']
            diagnosis['confidence'] = 70
            
        elif 'SyntaxError' in error_message:
            diagnosis['error_category'] = 'SyntaxError'
            diagnosis['summary'] = 'Invalid Python syntax'
            diagnosis['possible_causes'] = ['Missing colon', 'Unmatched parentheses', 'Incorrect indentation']
            diagnosis['confidence'] = 95
            
        elif 'IndexError' in error_message:
            diagnosis['error_category'] = 'IndexError'
            diagnosis['summary'] = 'List index out of range'
            diagnosis['possible_causes'] = ['Index too large', 'List is empty', 'Negative index on non-supported type']
            diagnosis['confidence'] = 85
            
        elif 'KeyError' in error_message:
            diagnosis['error_category'] = 'KeyError'
            diagnosis['summary'] = 'Dictionary key not found'
            diagnosis['possible_causes'] = ['Key does not exist', 'Case sensitivity issue', 'Using wrong dictionary']
            diagnosis['confidence'] = 85
        
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
                timeout=3
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
