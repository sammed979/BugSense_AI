"""
Verification Engine - Verify code repairs with syntax checks, linting, and execution.
"""
from typing import Dict, Any
from .code_analyzer import CodeAnalyzer
from sandbox.runners import get_runner
from django.conf import settings


class VerificationEngine:
    """Verify code repairs with multiple checks."""

    @staticmethod
    async def verify_repair(
        original_code: str,
        repaired_code: str,
        language: str
    ) -> Dict[str, Any]:
        """Verify a repair using language-appropriate checks."""
        results = {
            "syntax_check": "NOT_RUN",
            "lint_check": "NOT_RUN",
            "execution_check": "NOT_RUN",
            "passed": False,
            "status": "blocked",
        }

        # Syntax check — Python uses ast, JavaScript uses node --check, and
        # Java/C/C++ use their compilers through the sandbox runners.
        syntax_errors = CodeAnalyzer.check_syntax_for_language(repaired_code, language)
        if syntax_errors:
            results["syntax_check"] = "FAILED"
            results["syntax_errors"] = [
                {"line": err.line, "message": err.message} for err in syntax_errors
            ]
            return results
        else:
            results["syntax_check"] = "PASSED"

        # Lint check — Ruff is Python-only.
        if language == 'python':
            lint_issues = CodeAnalyzer.run_ruff(repaired_code)
            if lint_issues:
                results["lint_check"] = "WARNING"
                results["lint_issues"] = [
                    {"code": issue.code, "message": issue.message, "line": issue.line}
                    for issue in lint_issues
                ]
            else:
                results["lint_check"] = "PASSED"
        else:
            results["lint_check"] = "SKIPPED"

        # Execution check (if enabled) using the language-appropriate runner.
        execution_enabled = getattr(settings, 'EXECUTION_ENABLED', False)
        runner = get_runner(language)
        if execution_enabled and runner is not None:
            try:
                exit_code, stdout, stderr, duration_ms = runner.execute(repaired_code)

                if exit_code == 0:
                    results["execution_check"] = "PASSED"
                    results["execution_result"] = {
                        "exit_code": exit_code,
                        "stdout": stdout,
                        "stderr": stderr,
                        "duration_ms": round(duration_ms, 2)
                    }
                    results['status'] = 'passed'
                elif exit_code == 127 and 'not available' in stderr.lower():
                    results["execution_check"] = "ERROR"
                    results["execution_result"] = {
                        "exit_code": exit_code,
                        "stdout": stdout,
                        "stderr": stderr,
                        "duration_ms": round(duration_ms, 2)
                    }
                    results['status'] = 'blocked'
                else:
                    results["execution_check"] = "FAILED"
                    results["execution_result"] = {
                        "exit_code": exit_code,
                        "stdout": stdout,
                        "stderr": stderr,
                        "duration_ms": round(duration_ms, 2)
                    }
                    results['status'] = 'timed_out' if 'timed out' in stderr.lower() else 'failed'
            except Exception:
                results["execution_check"] = "ERROR"
                results["execution_error"] = 'Isolated execution could not be started.'
                results['status'] = 'blocked'
        else:
            results["execution_check"] = "SKIPPED"
            results['status'] = 'blocked'

        results["passed"] = (
            results["syntax_check"] == "PASSED" and
            results["execution_check"] == "PASSED"
        )

        return results
