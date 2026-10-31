"""
Python Runner - Secure Python code execution in isolated environment.
"""
import subprocess
import tempfile
import os
import shutil
import sys
from typing import Tuple
from django.conf import settings


class PythonRunner:
    """Secure Python code executor with resource limits."""

    @staticmethod
    def execute(code: str, timeout: int = None) -> Tuple[int, str, str, float]:
        """
        Execute Python code in a restricted environment.

        Args:
            code: Python source code to execute
            timeout: Execution timeout in seconds

        Returns:
            Tuple of (exit_code, stdout, stderr, duration_ms)
        """
        execution_enabled = getattr(settings, 'EXECUTION_ENABLED', False)
        if not execution_enabled:
            raise RuntimeError("Code execution is disabled. Configure EXECUTION_ENABLED=true.")

        execution_timeout = getattr(settings, 'EXECUTION_TIMEOUT_SECONDS', 5)
        timeout = timeout or execution_timeout

        temp_dir = tempfile.mkdtemp(prefix="bugsense_exec_")
        
        try:
            code_file = os.path.join(temp_dir, "main.py")
            with open(code_file, "w", encoding="utf-8") as f:
                f.write(code)

            env = {
                "PATH": os.environ.get("PATH", ""),
                "PYTHONPATH": "",
            }

            import time
            start_time = time.time()

            process = subprocess.Popen(
                [sys.executable, "-I", code_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                cwd=temp_dir,
                env=env,
                shell=False,
            )

            try:
                stdout, stderr = process.communicate(timeout=timeout)
                exit_code = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                exit_code = -1
                stdout = b""
                stderr = f"Execution timed out after {timeout} seconds".encode()

            duration_ms = (time.time() - start_time) * 1000

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            max_output = getattr(settings, 'EXECUTION_MAX_OUTPUT_BYTES', 65536)
            if len(stdout_str) > max_output:
                stdout_str = stdout_str[:max_output] + "\n\n[Output truncated]"
            if len(stderr_str) > max_output:
                stderr_str = stderr_str[:max_output] + "\n\n[Output truncated]"

            return exit_code, stdout_str, stderr_str, duration_ms

        except Exception as e:
            return -1, "", f"Execution error: {str(e)}", 0.0
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
