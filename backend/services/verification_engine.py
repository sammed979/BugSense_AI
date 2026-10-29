"""
Verification Engine - Verify code repairs with syntax checks, linting, and execution.
"""
from typing import Dict, Any
from .code_analyzer import CodeAnalyzer
from sandbox.python_runner import PythonRunner
from django.conf import settings


class VerificationEngine:
    """Verify code repairs with multiple checks."""

    @staticmethod
    async def verify_repair(
        original_code: str,
        repaired_code: str,
        language: str
    ) -> Dict[str, Any]:
        """Verify a repair by running checks."""
        results = {
            "syntax_check": "NOT_RUN",
            "lint_check": "NOT_RUN",
            "execution_check": "NOT_RUN",
            "passed": False,
        }

        # Syntax check
        syntax_errors = CodeAnalyzer.check_syntax(repaired_code)
        if syntax_errors:
            results["syntax_check"] = "FAILED"
            results["syntax_errors"] = [
                {"line": err.line, "message": err.message} for err in syntax_errors
            ]
            return results
        else:
            results["syntax_check"] = "PASSED"

        # Lint check
        lint_issues = CodeAnalyzer.run_ruff(repaired_code)
        if lint_issues:
            results["lint_check"] = "WARNING"
            results["lint_issues"] = [
                {"code": issue.code, "message": issue.message, "line": issue.line}
                for issue in lint_issues
            ]
        else:
            results["lint_check"] = "PASSED"

        # Execution check (if enabled)
        execution_enabled = getattr(settings, 'EXECUTION_ENABLED', False)
        if execution_enabled and language == 'python':
            try:
                exit_code, stdout, stderr, duration_ms = PythonRunner.execute(repaired_code)
                
                if exit_code == 0:
                    results["execution_check"] = "PASSED"
                    results["execution_result"] = {
                        "exit_code": exit_code,
                        "stdout": stdout,
                        "stderr": stderr,
                        "duration_ms": round(duration_ms, 2)
                    }
                else:
                    results["execution_check"] = "FAILED"
                    results["execution_result"] = {
                        "exit_code": exit_code,
                        "stdout": stdout,
                        "stderr": stderr,
                        "duration_ms": round(duration_ms, 2)
                    }
            except Exception as e:
                results["execution_check"] = "ERROR"
                results["execution_error"] = str(e)
        else:
            results["execution_check"] = "SKIPPED"

        results["passed"] = (
            results["syntax_check"] == "PASSED" and
            results["execution_check"] in ["PASSED", "SKIPPED"]
        )

        return results
