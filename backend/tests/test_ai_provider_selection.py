"""Regression checks for Gemini default selection and explicit repair fallback."""
import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace

from services.ai_service import AIService
from services.repair_engine import RepairEngine
from services.openai_client import create_chat_completion


class AIProviderSelectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_llm_provider_overrides_legacy_provider_priority(self):
        with patch.dict(os.environ, {
            "DEFAULT_LLM_PROVIDER": "openai",
            "AI_PROVIDER_PRIORITY": "gemini",
        }):
            self.assertEqual(AIService._provider_order(), ["openai"])

    async def test_openai_sync_client_is_closed_after_completion(self):
        with patch('openai.OpenAI') as fake_client:
            instance = fake_client.return_value.__enter__.return_value
            instance.chat.completions.create.return_value = SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content='print("ok")'))]
            )

            result = await create_chat_completion(
                'test-key',
                model='gpt-4o',
                messages=[],
                temperature=0,
            )

        self.assertEqual(result.choices[0].message.content, 'print("ok")')
        fake_client.assert_called_once_with(api_key='test-key', max_retries=0, timeout=35.0)
        fake_client.return_value.__enter__.assert_called_once()
        fake_client.return_value.__exit__.assert_called_once()

    async def test_openai_repair_parses_generated_code(self):
        repaired = 'def add(a, b):\n    return a + b'
        completion = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=repaired))]
        )
        with patch('services.repair_engine.create_chat_completion', new_callable=AsyncMock, return_value=completion) as request:
            result = await RepairEngine._repair_with_openai(
                'def add(a, b):\n    return a - b\n',
                'Expected addition',
                {'summary': 'The operator is incorrect.'},
                'python',
                'test-key',
                'gpt-4o',
            )

        self.assertEqual(result['repaired_code'], repaired)
        self.assertEqual(result['provider'], 'OpenAI')
        request.assert_awaited_once()

    async def test_openai_failure_logs_correlation_and_redacts_source_and_key(self):
        source = 'print("private-source")'
        api_key = 'sk-test-secret-token-value'
        with self.assertLogs('services.repair', level='ERROR') as captured:
            with patch(
                'services.repair_engine.create_chat_completion',
                new_callable=AsyncMock,
                side_effect=RuntimeError(f'Authorization: Bearer {api_key}'),
            ):
                result = await RepairEngine._repair_with_openai(
                    source,
                    'provider failure',
                    {},
                    'python',
                    api_key,
                    'gpt-4o',
                    'correlation-test-id',
                )

        log_output = '\n'.join(captured.output)
        self.assertEqual(result['error_type'], 'authentication')
        self.assertIn('request_id=correlation-test-id', log_output)
        self.assertIn('operation=repair_generation', log_output)
        self.assertIn('RuntimeError', log_output)
        self.assertNotIn(api_key, log_output)
        self.assertNotIn(source, log_output)

    async def test_missing_gemini_key_does_not_call_openai_or_return_heuristic(self):
        code = "print(user_name)"
        with patch.dict(os.environ, {
            "AI_PROVIDER_PRIORITY": "gemini",
            "OPENAI_API_KEY": "present-but-not-selected",
            "GEMINI_API_KEY": "",
            "GOOGLE_API_KEY": "",
        }):
            with patch.object(RepairEngine, "_repair_with_openai") as openai:
                result = await RepairEngine.generate_repair(
                    code, "NameError: name 'user_name' is not defined",
                    {"error_category": "NameError", "summary": "undefined name"}, "python"
                )
        self.assertEqual(result["error_type"], "missing_api_key")
        self.assertEqual(result["source"], "error")
        self.assertEqual(result["repaired_code"], code)
        openai.assert_not_called()

    async def test_invalid_credentials_are_classified(self):
        with patch("services.repair_engine.genai.Client", side_effect=Exception("403 API key invalid")):
            result = await RepairEngine._repair_with_gemini("print(x)", "NameError", {}, "python", "invalid", "gemini-2.5-flash")
        self.assertEqual(result["error_type"], "authentication")

    async def test_exhausted_quota_and_rate_limit_are_classified_without_retry(self):
        with patch("services.repair_engine.genai.Client", side_effect=Exception("429 RESOURCE_EXHAUSTED quota exceeded")) as client:
            result = await RepairEngine._repair_with_gemini("print(x)", "NameError", {}, "python", "test-key", "gemini-2.5-flash")
        self.assertEqual(result["error_type"], "quota_exhausted")
        client.assert_called_once()

    async def test_default_order_does_not_select_openai(self):
        with patch.dict(os.environ, {
            "AI_PROVIDER_PRIORITY": "gemini",
            "OPENAI_API_KEY": "present-but-not-selected",
            "GEMINI_API_KEY": "",
            "GOOGLE_API_KEY": "",
        }):
            result = await RepairEngine.generate_repair(
                "print(x)", "NameError", {"error_category": "NameError", "summary": "undefined name"}, "python"
            )
        self.assertEqual(result["error_type"], "missing_api_key")
        self.assertEqual(result["source"], "error")


if __name__ == "__main__":
    unittest.main()
