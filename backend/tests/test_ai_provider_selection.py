"""Regression checks for Gemini default selection and explicit repair fallback."""
import asyncio
import os
import unittest
from unittest.mock import patch

from services.repair_engine import RepairEngine


class AIProviderSelectionTests(unittest.IsolatedAsyncioTestCase):
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
