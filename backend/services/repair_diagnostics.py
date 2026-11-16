"""Secret-safe diagnostics for AI repair failures."""
import logging
import os
import re
import traceback


logger = logging.getLogger('services.repair')
_SECRET_ENV_NAMES = (
    'OPENAI_API_KEY',
    'GEMINI_API_KEY',
    'GOOGLE_API_KEY',
    'DJANGO_SECRET_KEY',
    'DATABASE_URL',
)
_BEARER_PATTERN = re.compile(r'(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,\'"]+')
_API_KEY_PATTERN = re.compile(r'\bsk-[A-Za-z0-9_-]{12,}\b')


def _redact(text, sensitive_values=()):
    for value in (*sensitive_values, *(os.environ.get(name, '') for name in _SECRET_ENV_NAMES)):
        if value:
            text = text.replace(value, '[REDACTED]')
    text = _BEARER_PATTERN.sub(r'\1[REDACTED]', text)
    return _API_KEY_PATTERN.sub('[REDACTED]', text)


def log_provider_exception(request_id, provider, operation, error, sensitive_values=()):
    safe_message = _redact(f'{type(error).__name__}: {error}', sensitive_values)[:1000]
    safe_traceback = _redact(traceback.format_exc(), sensitive_values)
    logger.error(
        'AI operation failed request_id=%s provider=%s operation=%s '
        'exception_class=%s safe_message=%s\n%s',
        request_id,
        provider,
        operation,
        type(error).__name__,
        safe_message,
        safe_traceback,
    )


def log_provider_failure(request_id, provider, operation, error_type):
    logger.warning(
        'AI provider returned failure request_id=%s provider=%s operation=%s error_type=%s',
        request_id,
        provider,
        operation,
        error_type,
    )
