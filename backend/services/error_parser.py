"""
Error Parser - Parse Python tracebacks and error messages.
"""
import re
from typing import Optional, List
from dataclasses import dataclass, field


@dataclass
class TracebackFrame:
    file_path: str
    line_number: int
    function_name: str
    code_line: Optional[str] = None
    log_line_number: Optional[int] = None
    source_log_line_number: Optional[int] = None


@dataclass
class ParsedTraceback:
    exception_type: str
    exception_message: str
    frames: List[TracebackFrame]
    raw_traceback: str
    traceback_start_line: int = 1
    traceback_end_line: int = 1
    exception_line_number: Optional[int] = None
    exception_line: Optional[str] = None
    frame_log_lines: List[int] = field(default_factory=list)
    source_log_lines: List[int] = field(default_factory=list)
    preceding_relation: Optional[str] = None


class ErrorParser:
    """Parse Python tracebacks to extract error information."""

    TRACEBACK_LINE_PATTERN = re.compile(
        r'File [\'"](?P<file>[^\'"]+)[\'"], line (?P<line>\d+), in (?P<function>[^\s]+)'
    )
    TRACEBACK_HEADER_PATTERN = re.compile(
        r'Traceback \(most recent call (?:last|first)\):',
        re.IGNORECASE,
    )
    EXCEPTION_PATTERN = re.compile(
        r'^(?P<type>(?:[A-Za-z_]\w*\.)*[A-Z][A-Za-z0-9_]*)'
        r'(?::\s*(?P<message>.*))?$'
    )
    TRACEBACK_TRANSITION = re.compile(
        r'^(?:During handling of the above exception|The above exception was the direct cause)',
        re.IGNORECASE,
    )
    LOG_LEVEL_PREFIX = re.compile(r'^(?:ERROR|CRITICAL|FATAL)\s*[:\]-]\s*', re.IGNORECASE)
    NON_ERROR_LOG_PREFIX = re.compile(r'^(?:TRACE|DEBUG|INFO|NOTICE|WARN(?:ING)?)\s*:', re.IGNORECASE)

    @staticmethod
    def parse_tracebacks(traceback_text: str) -> List[ParsedTraceback]:
        """Parse all Python traceback blocks while retaining their source context."""
        if not traceback_text:
            return []

        lines = traceback_text.splitlines()
        starts = [
            index for index, line in enumerate(lines)
            if ErrorParser.TRACEBACK_HEADER_PATTERN.search(line)
        ]
        parsed = []
        for position, start in enumerate(starts):
            stop = starts[position + 1] if position + 1 < len(starts) else len(lines)
            preceding_relation = None
            if position:
                preceding = '\n'.join(lines[starts[position - 1]:start])
                if re.search(r'The above exception was the direct cause', preceding, re.I):
                    preceding_relation = 'direct_cause'
                elif re.search(r'During handling of the above exception', preceding, re.I):
                    preceding_relation = 'during_handling'
            header_indent = len(lines[start]) - len(lines[start].lstrip())
            exception_index = None
            exception_type = None
            exception_message = ''
            exception_line = None

            for index in range(stop - 1, start, -1):
                raw_line = lines[index]
                indent = len(raw_line) - len(raw_line.lstrip())
                if indent > header_indent:
                    continue
                candidate = raw_line.strip()
                if not candidate or ErrorParser.NON_ERROR_LOG_PREFIX.match(candidate):
                    continue
                candidate = ErrorParser.LOG_LEVEL_PREFIX.sub('', candidate, count=1)
                match = ErrorParser.EXCEPTION_PATTERN.match(candidate)
                if not match:
                    continue
                exception_index = index
                exception_type = match.group('type').rsplit('.', 1)[-1]
                exception_message = (match.group('message') or '').strip()
                exception_line = raw_line.strip()
                break

            frame_matches = []
            frame_stop = exception_index if exception_index is not None else stop
            for index in range(start + 1, frame_stop):
                match = ErrorParser.TRACEBACK_LINE_PATTERN.search(lines[index])
                if match:
                    frame_matches.append((index, match))

            frames = []
            frame_log_lines = []
            source_log_lines = []
            for frame_position, (index, match) in enumerate(frame_matches):
                next_frame = (
                    frame_matches[frame_position + 1][0]
                    if frame_position + 1 < len(frame_matches)
                    else frame_stop
                )
                source_line = None
                source_index = None
                for candidate_index in range(index + 1, next_frame):
                    candidate = lines[candidate_index].strip()
                    if not candidate:
                        continue
                    if (
                        ErrorParser.TRACEBACK_LINE_PATTERN.search(candidate)
                        or ErrorParser.TRACEBACK_HEADER_PATTERN.search(candidate)
                        or ErrorParser.TRACEBACK_TRANSITION.match(candidate)
                    ):
                        break
                    if set(candidate) <= {'^', '~'}:
                        continue
                    if ErrorParser.EXCEPTION_PATTERN.match(candidate):
                        break
                    source_line = lines[candidate_index].rstrip()
                    source_index = candidate_index
                    break

                frames.append(TracebackFrame(
                    file_path=match.group('file'),
                    line_number=int(match.group('line')),
                    function_name=match.group('function'),
                    code_line=source_line,
                    log_line_number=index + 1,
                    source_log_line_number=source_index + 1 if source_index is not None else None,
                ))
                frame_log_lines.append(index + 1)
                if source_index is not None:
                    source_log_lines.append(source_index + 1)

            parsed.append(ParsedTraceback(
                exception_type=exception_type or 'UnknownError',
                exception_message=exception_message,
                frames=frames,
                raw_traceback='\n'.join(lines[start:stop]),
                traceback_start_line=start + 1,
                traceback_end_line=stop,
                exception_line_number=exception_index + 1 if exception_index is not None else None,
                exception_line=exception_line,
                frame_log_lines=frame_log_lines,
                source_log_lines=source_log_lines,
                preceding_relation=preceding_relation,
            ))
        return parsed

    @staticmethod
    def parse_traceback(traceback_text: str) -> Optional[ParsedTraceback]:
        """Return the final traceback block for backward compatibility."""
        tracebacks = ErrorParser.parse_tracebacks(traceback_text)
        return tracebacks[-1] if tracebacks else None

    @staticmethod
    def extract_error_type(error_message: str) -> Optional[str]:
        """Extract error type from a simple error message."""
        if not error_message:
            return None

        match = re.match(r'^((?:[A-Za-z_]\w*\.)*[A-Za-z_]\w*):', error_message.strip())
        if match:
            return match.group(1).rsplit('.', 1)[-1]

        return None
