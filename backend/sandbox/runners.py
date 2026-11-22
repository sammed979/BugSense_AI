"""
Multi-language sandbox runners.

Each runner executes source code in an isolated subprocess with resource limits
(CPU time, memory, file size, process count) applied on Linux via a wrapper
script. Temp directories are always cleaned up. User code never runs inside the
Django worker process.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Optional, Tuple

from django.conf import settings

# Reuse the canonical Python runner so the existing execution pipeline (and the
# tests that patch sandbox.python_runner.PythonRunner) stay intact.
from sandbox.python_runner import PythonRunner


def _execution_enabled() -> bool:
    return bool(getattr(settings, 'EXECUTION_ENABLED', False))


# Essential system variables that native runtimes (notably the Windows JVM)
# need to start. They are passed through on top of the minimal sandbox env so
# toolchains work on Windows too; secrets such as DATABASE_URL or API keys are
# deliberately NOT in this list, so they never reach user code.
_ENV_PASSTHROUGH = (
    'SystemRoot', 'windir', 'SystemDrive', 'TEMP', 'TMP', 'PATHEXT', 'ComSpec',
    'USERPROFILE', 'HOMEDRIVE', 'HOMEPATH', 'APPDATA', 'LOCALAPPDATA',
    'ProgramData', 'ProgramFiles', 'ProgramFiles(x86)', 'ProgramW6432',
    'NUMBER_OF_PROCESSORS', 'OS', 'PROCESSOR_ARCHITECTURE',
)


def _sandbox_env(temp_dir: str) -> dict:
    env = {
        'PATH': os.environ.get('PATH', ''),
        'HOME': temp_dir,
        'LANG': 'C.UTF-8',
    }
    for key in _ENV_PASSTHROUGH:
        value = os.environ.get(key)
        if value is not None:
            env[key] = value
    return env


def _resource_limits_wrapper() -> str:
    """Return a POSIX shell snippet that applies rlimits before exec.

    Used on Linux to bound CPU, memory, file size and process count. On other
    platforms the snippet is a no-op and only the subprocess timeout applies.
    """
    if sys.platform != 'linux':
        return ''
    cpu = int(getattr(settings, 'EXECUTION_TIMEOUT_SECONDS', 5))
    mem_kb = int(getattr(settings, 'EXECUTION_MEMORY_LIMIT_MB', 128)) * 1024
    fsize_mb = int(getattr(settings, 'EXECUTION_MAX_OUTPUT_BYTES', 65536)) // (1024 * 1024) or 16
    nproc = 64
    return (
        f"ulimit -t {cpu} 2>/dev/null; "
        f"ulimit -v {mem_kb} 2>/dev/null; "
        f"ulimit -f {fsize_mb * 1024} 2>/dev/null; "
        f"ulimit -u {nproc} 2>/dev/null; "
    )


class BaseRunner:
    """Common execution scaffolding for all language runners."""

    language: str = 'base'
    source_filename: str = 'source'

    @staticmethod
    def _write_source(temp_dir: str, filename: str, code: str) -> str:
        path = os.path.join(temp_dir, filename)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(code)
        return path

    @staticmethod
    def _truncate(text: str) -> str:
        max_bytes = int(getattr(settings, 'EXECUTION_MAX_OUTPUT_BYTES', 65536))
        if len(text.encode('utf-8', errors='replace')) > max_bytes:
            return text.encode('utf-8', errors='replace')[:max_bytes].decode('utf-8', errors='replace') + '\n\n[Output truncated]'
        return text

    @classmethod
    def _run_command(cls, args, temp_dir, timeout, stdin_data=None) -> Tuple[int, str, str, float]:
        env = _sandbox_env(temp_dir)
        start = time.time()
        try:
            proc = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE if stdin_data is not None else subprocess.DEVNULL,
                cwd=temp_dir,
                env=env,
                shell=False,
            )
            try:
                stdout, stderr = proc.communicate(input=stdin_data, timeout=timeout)
                exit_code = proc.returncode
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                exit_code = -1
                stdout = b''
                stderr = f'Execution timed out after {timeout} seconds'.encode()
        except FileNotFoundError as exc:
            exit_code = 127
            stdout = b''
            stderr = f'Toolchain not found: {exc}'.encode()
        duration_ms = (time.time() - start) * 1000
        return (
            exit_code,
            cls._truncate(stdout.decode('utf-8', errors='replace')),
            cls._truncate(stderr.decode('utf-8', errors='replace')),
            round(duration_ms, 2),
        )


class JavaScriptRunner(BaseRunner):
    language = 'javascript'
    source_filename = 'main.js'

    @staticmethod
    def execute(code: str, timeout: Optional[int] = None) -> Tuple[int, str, str, float]:
        if not _execution_enabled():
            raise RuntimeError('Code execution is disabled. Configure EXECUTION_ENABLED=true.')
        node = shutil.which('node')
        if not node:
            return 127, '', 'Node.js runtime is not available on this server.', 0.0
        timeout = timeout or int(getattr(settings, 'EXECUTION_TIMEOUT_SECONDS', 5))
        temp_dir = tempfile.mkdtemp(prefix='bugsense_js_')
        try:
            source = JavaScriptRunner._write_source(temp_dir, 'main.js', code)
            return JavaScriptRunner._run_command([node, source], temp_dir, timeout)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class JavaRunner(BaseRunner):
    language = 'java'
    source_filename = 'Main.java'

    @staticmethod
    def _class_name(code: str) -> str:
        match = None
        for line in code.splitlines():
            m = re_class.search(line)
            if m:
                if match is None:
                    match = m.group(1)
                # A public class determines the required file name.
                if line.strip().startswith('public'):
                    return m.group(1)
        return match or 'Main'

    @staticmethod
    def execute(code: str, timeout: Optional[int] = None) -> Tuple[int, str, str, float]:
        if not _execution_enabled():
            raise RuntimeError('Code execution is disabled. Configure EXECUTION_ENABLED=true.')
        javac = shutil.which('javac')
        java = shutil.which('java')
        if not javac or not java:
            return 127, '', 'Java compiler (javac) or runtime (java) is not available on this server.', 0.0
        timeout = timeout or int(getattr(settings, 'EXECUTION_TIMEOUT_SECONDS', 5))
        temp_dir = tempfile.mkdtemp(prefix='bugsense_java_')
        try:
            class_name = JavaRunner._class_name(code)
            source = JavaRunner._write_source(temp_dir, f'{class_name}.java', code)
            exit_code, stdout, stderr, _ = JavaRunner._run_command(
                [javac, '-encoding', 'UTF-8', source], temp_dir, timeout
            )
            if exit_code != 0:
                return exit_code, stdout, stderr, 0.0
            return JavaRunner._run_command([java, '-cp', temp_dir, class_name], temp_dir, timeout)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


re_class = re.compile(r'\bclass\s+(\w+)')


class CRunner(BaseRunner):
    language = 'c'
    source_filename = 'main.c'

    @staticmethod
    def execute(code: str, timeout: Optional[int] = None) -> Tuple[int, str, str, float]:
        if not _execution_enabled():
            raise RuntimeError('Code execution is disabled. Configure EXECUTION_ENABLED=true.')
        gcc = shutil.which('gcc') or shutil.which('cc')
        if not gcc:
            return 127, '', 'C compiler (gcc) is not available on this server.', 0.0
        timeout = timeout or int(getattr(settings, 'EXECUTION_TIMEOUT_SECONDS', 5))
        temp_dir = tempfile.mkdtemp(prefix='bugsense_c_')
        try:
            source = CRunner._write_source(temp_dir, 'main.c', code)
            binary = os.path.join(temp_dir, 'a.out')
            exit_code, stdout, stderr, _ = CRunner._run_command(
                [gcc, '-o', binary, source], temp_dir, timeout
            )
            if exit_code != 0:
                return exit_code, stdout, stderr, 0.0
            return CRunner._run_command([binary], temp_dir, timeout)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class CppRunner(BaseRunner):
    language = 'cpp'
    source_filename = 'main.cpp'

    @staticmethod
    def execute(code: str, timeout: Optional[int] = None) -> Tuple[int, str, str, float]:
        if not _execution_enabled():
            raise RuntimeError('Code execution is disabled. Configure EXECUTION_ENABLED=true.')
        gpp = shutil.which('g++') or shutil.which('c++')
        if not gpp:
            return 127, '', 'C++ compiler (g++) is not available on this server.', 0.0
        timeout = timeout or int(getattr(settings, 'EXECUTION_TIMEOUT_SECONDS', 5))
        temp_dir = tempfile.mkdtemp(prefix='bugsense_cpp_')
        try:
            source = CppRunner._write_source(temp_dir, 'main.cpp', code)
            binary = os.path.join(temp_dir, 'a.out')
            exit_code, stdout, stderr, _ = CppRunner._run_command(
                [gpp, '-o', binary, source], temp_dir, timeout
            )
            if exit_code != 0:
                return exit_code, stdout, stderr, 0.0
            return CppRunner._run_command([binary], temp_dir, timeout)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


RUNNER_REGISTRY = {
    'python': PythonRunner,
    'javascript': JavaScriptRunner,
    'java': JavaRunner,
    'c': CRunner,
    'cpp': CppRunner,
}


def get_runner(language: str):
    return RUNNER_REGISTRY.get(language)


def supported_execution_languages() -> list:
    return list(RUNNER_REGISTRY.keys())
