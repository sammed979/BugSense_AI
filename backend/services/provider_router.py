"""Per-user provider routing shared by analysis and repair."""
import os
from asgiref.sync import sync_to_async
from services.ai_service import AIService
from services.repair_engine import RepairEngine
from services.local_repair_engine import LocalRepairEngine
from apps.accounts.models import AIProviderSettings


TRANSIENT = {'quota_exhausted', 'rate_limited', 'timeout', 'network', 'service_unavailable', 'provider_error'}


class AIProvider:
    """Provider adapter contract shared by analysis and repair."""
    name = 'provider'

    async def analyze_code(self, error_message, traceback, source_code, language):
        raise NotImplementedError

    async def generate_repair(self, source_code, error_message, diagnosis, language, traceback=''):
        raise NotImplementedError

    def explain_error(self, source_code, error_message):
        from services.code_analyzer import CodeAnalyzer
        return CodeAnalyzer.analyze_error_context(source_code, error_message)

    def check_availability(self):
        raise NotImplementedError


class GeminiProvider(AIProvider):
    name = 'gemini'

    async def analyze_code(self, error_message, traceback, source_code, language):
        return await AIService._analyze_with_gemini(error_message, traceback, source_code, language)

    async def generate_repair(self, source_code, error_message, diagnosis, language, traceback=''):
        return await RepairEngine._repair_with_gemini(source_code, error_message, diagnosis, language, os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY') or '', os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'), traceback)

    def check_availability(self):
        return AIService.check_gemini_model_access()


class OpenAIProvider(AIProvider):
    name = 'openai'

    async def analyze_code(self, error_message, traceback, source_code, language):
        return await AIService._analyze_with_openai(error_message, traceback, source_code, language)

    async def generate_repair(self, source_code, error_message, diagnosis, language, traceback=''):
        return await RepairEngine._repair_with_openai(source_code, error_message, diagnosis, language, os.getenv('OPENAI_API_KEY') or '', os.getenv('OPENAI_MODEL', 'gpt-4o'))

    def check_availability(self):
        from services.ai_service import OPENAI_AVAILABLE
        configured = bool(os.getenv('OPENAI_API_KEY'))
        state = 'ready' if configured and OPENAI_AVAILABLE else ('missing_api_key' if not configured else 'sdk_unavailable')
        return {'provider': self.name, 'status': state, 'ready': state == 'ready'}


class LocalRepairProvider(AIProvider):
    name = 'local'

    async def analyze_code(self, error_message, traceback, source_code, language):
        return {'provider': 'Local Repair Engine', 'source': 'local_analysis', **self.explain_error(source_code, error_message or traceback)}

    async def generate_repair(self, source_code, error_message, diagnosis, language, traceback=''):
        return LocalRepairEngine.generate_repair(source_code, error_message)

    def check_availability(self):
        return {'provider': self.name, 'status': 'ready', 'ready': True}


PROVIDERS = {'gemini': GeminiProvider(), 'openai': OpenAIProvider(), 'local': LocalRepairProvider()}


def settings_for(user):
    return AIProviderSettings.objects.get_or_create(user=user)[0]


def _mode(settings):
    return settings.mode or os.getenv('DEFAULT_AI_PROVIDER', 'gemini')


async def analyze(user, error_message, traceback, source_code, language, provider_settings=None):
    prefs = provider_settings or await sync_to_async(settings_for)(user)
    mode = _mode(prefs)
    if mode == 'local':
        result = await PROVIDERS['local'].analyze_code(error_message, traceback, source_code, language)
        return {'status': 'complete', **result}
    provider = prefs.primary_provider if mode == 'automatic' else mode
    if mode == 'automatic' and not prefs.automatic_fallback:
        provider = prefs.primary_provider
    result = await _analyze_provider(provider, error_message, traceback, source_code, language)
    if mode == 'automatic' and prefs.automatic_fallback and result.get('error') and result.get('error_type') in TRANSIENT:
        fallback = await _analyze_provider(prefs.secondary_provider, error_message, traceback, source_code, language)
        if not fallback.get('error'):
            fallback['fallback_from'] = {'provider': provider, 'error_type': result.get('error_type')}
            return fallback
        from services.code_analyzer import CodeAnalyzer
        return {'status': 'complete', 'provider': 'Local Repair Engine', 'source': 'local_analysis', 'fallback_from': [{'provider': provider, 'error_type': result.get('error_type')}, {'provider': prefs.secondary_provider, 'error_type': fallback.get('error_type')}], **CodeAnalyzer.analyze_error_context(source_code, error_message or traceback)}
    return result


async def _analyze_provider(provider, error_message, traceback, source_code, language):
    if provider == 'gemini' and not (os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')):
        return {'error': 'Gemini API key is not configured on the backend.', 'error_type': 'missing_api_key', 'provider': 'Gemini', 'status': 'failed'}
    if provider == 'openai' and not os.getenv('OPENAI_API_KEY'):
        return {'error': 'OpenAI API key is not configured on the backend.', 'error_type': 'missing_api_key', 'provider': 'OpenAI', 'status': 'failed'}
    if provider == 'gemini':
        result = await PROVIDERS['gemini'].analyze_code(error_message, traceback, source_code, language)
    elif provider == 'openai':
        result = await PROVIDERS['openai'].analyze_code(error_message, traceback, source_code, language)
    else:
        return {'error': 'Unknown provider selection.', 'error_type': 'invalid_provider', 'provider': provider}
    result.setdefault('provider', provider)
    if result.get('error') and not result.get('error_type'):
        result['error_type'] = AIService._classify_provider_error(result.get('message') or result['error'])
    if result.get('error'):
        result['error'] = f'{provider.title()} {result["error_type"].replace("_", " ")}. Check backend configuration, model access, quota, or connectivity.'
        result['message'] = result['error']
    result['status'] = 'failed' if result.get('error') else 'complete'
    return result


async def repair(user, source_code, error_message, diagnosis, language, traceback='', provider_settings=None):
    prefs = provider_settings or await sync_to_async(settings_for)(user)
    mode = _mode(prefs)
    if mode == 'local':
        result = LocalRepairEngine.generate_repair(source_code, error_message)
        result['provider'] = 'Local Repair Engine'
        return result
    providers = [mode] if mode in ('gemini', 'openai') else [prefs.primary_provider]
    if mode == 'automatic' and prefs.automatic_fallback:
        providers.append(prefs.secondary_provider)
    failures = []
    for provider in providers:
        key = (os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')) if provider == 'gemini' else os.getenv('OPENAI_API_KEY')
        if not key:
            result = {'error': f'{provider.title()} API key is not configured on the backend.', 'error_type': 'missing_api_key', 'provider': provider, 'source': 'error'}
            failures.append({'provider': provider, 'error_type': 'missing_api_key'})
            if mode != 'automatic' or not prefs.automatic_fallback:
                return result
            continue
        if provider == 'gemini':
            result = await PROVIDERS['gemini'].generate_repair(source_code, error_message, diagnosis, language, traceback)
            result.setdefault('provider', 'Gemini')
            result.setdefault('source', 'ai_gemini')
        else:
            result = await PROVIDERS['openai'].generate_repair(source_code, error_message, diagnosis, language, traceback)
            result.setdefault('provider', 'OpenAI')
            result.setdefault('source', 'ai_openai')
        if not result.get('error') and result.get('repaired_code') and result['repaired_code'] != source_code:
            return result
        error_type = result.get('error_type') or AIService._classify_provider_error(result.get('error', 'provider error'))
        result['error_type'] = error_type
        failures.append({'provider': provider, 'error_type': error_type})
        # Explicit selections are single-provider. Automatic only falls through for transient failures.
        if mode != 'automatic' or not prefs.automatic_fallback or error_type not in TRANSIENT:
            return result
    local = LocalRepairEngine.generate_repair(source_code, error_message)
    if local.get('success'):
        local['fallback_from'] = failures
        local['provider'] = 'Local Repair Engine'
        return local
    return {'error': 'Configured providers failed and no safe local repair was found.', 'error_type': failures[-1]['error_type'] if failures else 'unsupported_or_ambiguous', 'provider': failures[-1]['provider'] if failures else 'local', 'fallback_from': failures, 'source': 'error'}
