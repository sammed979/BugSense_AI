"""
Language Detector - Automatic programming language detection from source code.

Uses file extension (when available) plus keyword, import/header, declaration,
and syntax-pattern scoring. Confirms Python with ast.parse and JavaScript with
node --check when the runtime is available.
"""
import ast
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Optional, Tuple


SUPPORTED_LANGUAGES = ('python', 'java', 'c', 'cpp', 'javascript')

EXTENSION_MAP = {
    '.py': 'python',
    '.java': 'java',
    '.c': 'c',
    '.h': 'c',
    '.cpp': 'cpp',
    '.cc': 'cpp',
    '.cxx': 'cpp',
    '.hpp': 'cpp',
    '.hxx': 'cpp',
    '.js': 'javascript',
    '.mjs': 'javascript',
}

# Strong, language-unique keywords / patterns. Each match adds to the score.
LANGUAGE_SIGNATURES = {
    'python': [
        r'(?m)^\s*def\s+\w+\s*\(',
        r'(?m)^\s*class\s+\w+(\(|:)',
        r'(?m)^\s*import\s+\w+',
        r'(?m)^\s*from\s+\w+\s+import\s+',
        r'(?m)^\s*print\s*\(',
        r'__name__\s*==\s*[\'"]__main__[\'"]',
        r'(?m)^\s*if\s+__name__\s*==\s*[\'"]__main__[\'"]',
        r'(?m)^\s*async\s+def\s+',
        r'lambda\s+\w',
        r'(?m)^\s*elif\s+',
    ],
    'java': [
        r'(?m)^\s*public\s+class\s+\w+',
        r'(?m)^\s*class\s+\w+\s*(extends|implements|\{)',
        r'(?m)^\s*import\s+java\.[\w.]+;',
        r'(?m)^\s*package\s+[\w.]+;',
        r'public\s+static\s+void\s+main\s*\(',
        r'System\.out\.println',
        r'(?m)^\s*(public|private|protected)\s+(static\s+)?(final\s+)?\w[\w<>\[\]]*\s+\w+\s*\(',
    ],
    'c': [
        r'#include\s*<stdio\.h>',
        r'#include\s*<stdlib\.h>',
        r'#include\s*<string\.h>',
        r'#include\s*<unistd\.h>',
        r'printf\s*\(',
        r'scanf\s*\(',
        r'(?m)^\s*malloc\s*\(',
        r'(?m)^\s*free\s*\(',
        r'(?m)^\s*int\s+main\s*\(',
        r'(?m)^\s*typedef\s+struct\s+',
    ],
    'cpp': [
        r'#include\s*<iostream>',
        r'#include\s*<vector>',
        r'#include\s*<string>',
        r'#include\s*<map>',
        r'std::cout',
        r'std::cin',
        r'std::endl',
        r'using\s+namespace\s+std\s*;',
        r'(?m)^\s*template\s*<',
        r'(?m)^\s*class\s+\w+\s*\{',
        r'new\s+\w+\s*\(',
        r'->\w+\s*\(',
    ],
    'javascript': [
        r'console\.log\s*\(',
        r'(?m)^\s*const\s+\w+\s*=',
        r'(?m)^\s*let\s+\w+\s*=',
        r'(?m)^\s*var\s+\w+\s*=',
        r'(?m)^\s*function\s+\w+\s*\(',
        r'(?m)^\s*(async\s+)?\w+\s*=\s*(async\s*)?\([^)]*\)\s*=>',
        r'\brequire\s*\(',
        r'(?m)^\s*import\s+.*from\s+[\'"]',
        r'(?m)^\s*export\s+(default\s+)?(class|function|const|let)\s+',
        r'\bdocument\.',
        r'\bwindow\.',
        r'then\s*\(\s*\(?\w+\)?\s*=>',
    ],
}

# Disambiguation: C and C++ share #include. If iostream / vector / std:: present
# it is C++; if only stdio/stdlib/string/unistd it is C.
C_ONLY_HEADERS = {'<stdio.h>', '<stdlib.h>', '<string.h>', '<unistd.h>', '<math.h>', '<time.h>'}


@dataclass
class DetectionResult:
    language: Optional[str]
    confidence: float
    confident: bool
    evidence: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'language': self.language,
            'confidence': round(self.confidence, 3),
            'confident': self.confident,
            'evidence': self.evidence,
        }


class LanguageDetector:
    """Detect the programming language of source code with a confidence score."""

    CONFIDENCE_THRESHOLD = 0.60
    MIN_SCORE = 2

    @staticmethod
    def detect(source_code: str, filename: Optional[str] = None) -> DetectionResult:
        code = source_code or ''
        if not code.strip() and not filename:
            return DetectionResult(None, 0.0, False)

        scores = {lang: 0.0 for lang in SUPPORTED_LANGUAGES}
        evidence = {lang: [] for lang in SUPPORTED_LANGUAGES}

        # 1. File extension signal (bonus, not decisive).
        ext_lang = None
        if filename:
            import os
            _, ext = os.path.splitext(filename.lower())
            ext_lang = EXTENSION_MAP.get(ext)
            if ext_lang:
                scores[ext_lang] += 1.5
                evidence[ext_lang].append(f'file extension {ext}')

        # 2. Keyword / syntax pattern scoring.
        for lang, patterns in LANGUAGE_SIGNATURES.items():
            for pattern in patterns:
                if re.search(pattern, code):
                    scores[lang] += 1.0
                    evidence[lang].append(pattern.strip()[:40])

        # 3. C vs C++ disambiguation on headers.
        cpp_headers = bool(re.search(r'#include\s*<(iostream|vector|string|map|set|algorithm|memory|fstream)>', code))
        c_headers = bool(re.search(r'#include\s*<(stdio|stdlib|string|unistd|math|time)\.h>', code))
        if cpp_headers and not c_headers:
            scores['cpp'] += 2.0
            evidence['cpp'].append('C++ standard library headers')
        elif c_headers and not cpp_headers:
            scores['c'] += 1.5
            evidence['c'].append('C standard library headers')

        # 4. Confirm with actual parsers when possible.
        confirmed = LanguageDetector._confirm_with_parsers(code)
        for lang, ok in confirmed.items():
            if ok:
                scores[lang] += 3.0
                evidence[lang].append(f'{lang} parser accepted the code')

        # 5. Pick the highest score.
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        top_lang, top_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0

        if top_score < LanguageDetector.MIN_SCORE:
            return DetectionResult(None, 0.0, False, evidence)

        # Confidence: ratio of top score to total, with a margin over second.
        total = sum(scores.values()) or 1.0
        confidence = min(1.0, (top_score / total) * (1.0 + (top_score - second_score) / max(top_score, 1.0)))

        confident = (
            confidence >= LanguageDetector.CONFIDENCE_THRESHOLD
            and (top_score - second_score) >= 1.0
        )

        # If extension strongly disagreed and pattern score is weak, stay unconfident.
        if ext_lang and ext_lang != top_lang and top_score < 3.0:
            confident = False

        return DetectionResult(
            language=top_lang if confident else None,
            confidence=confidence,
            confident=confident,
            evidence={k: v for k, v in evidence.items() if v},
        )

    @staticmethod
    def _confirm_with_parsers(code: str) -> dict:
        result = {'python': False, 'javascript': False}
        # Python AST is cheap and always available.
        try:
            ast.parse(code)
            result['python'] = True
        except (SyntaxError, ValueError):
            result['python'] = False

        # JavaScript: use node --check if available.
        node = shutil.which('node')
        if node:
            try:
                proc = subprocess.run(
                    [node, '--check', '-'],
                    input=code,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                result['javascript'] = proc.returncode == 0
            except (subprocess.SubprocessError, OSError):
                result['javascript'] = False
        return result
