"""
Error Parser - Parse Python tracebacks and error messages.
"""
import re
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class TracebackFrame:
    file_path: str
    line_number: int
    function_name: str
    code_line: Optional[str] = None


@dataclass
class ParsedTraceback:
    exception_type: str
    exception_message: str
    frames: List[TracebackFrame]
    raw_traceback: str


class ErrorParser:
    """Parse Python tracebacks to extract error information."""

    TRACEBACK_LINE_PATTERN = re.compile(
        r'File "(?P<file>[^"]+)", line (?P<line>\d+), in (?P<function>\w+)'
    )
    
    EXCEPTION_PATTERN = re.compile(
        r'(?P<type>\w+)(?::\s*(?P<message>.+))?'
    )

    @staticmethod
    def parse_traceback(traceback_text: str) -> Optional[ParsedTraceback]:
        """Parse a Python traceback string."""
        if not traceback_text:
            return None

        lines = traceback_text.strip().split('\n')
        frames = []
        exception_type = None
        exception_message = ""

        for i, line in enumerate(lines):
            frame_match = ErrorParser.TRACEBACK_LINE_PATTERN.search(line)
            if frame_match:
                frame = TracebackFrame(
                    file_path=frame_match.group('file'),
                    line_number=int(frame_match.group('line')),
                    function_name=frame_match.group('function'),
                )
                
                if i + 1 < len(lines) and lines[i + 1].strip().startswith('    '):
                    frame.code_line = lines[i + 1].strip()
                
                frames.append(frame)
                continue

            if i == len(lines) - 1 or (i > 0 and not lines[i + 1].strip()):
                exception_match = ErrorParser.EXCEPTION_PATTERN.match(line.strip())
                if exception_match:
                    exception_type = exception_match.group('type')
                    exception_message = exception_match.group('message') or ""

        if not exception_type and not frames:
            return None

        return ParsedTraceback(
            exception_type=exception_type or "UnknownError",
            exception_message=exception_message,
            frames=frames,
            raw_traceback=traceback_text
        )

    @staticmethod
    def extract_error_type(error_message: str) -> Optional[str]:
        """Extract error type from a simple error message."""
        if not error_message:
            return None

        match = re.match(r'^(\w+):', error_message.strip())
        if match:
            return match.group(1)

        return None
