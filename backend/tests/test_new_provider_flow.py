from unittest.mock import AsyncMock, patch
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from apps.accounts.models import AIProviderSettings
from services.local_repair_engine import LocalRepairEngine
from sandbox.python_runner import PythonRunner

SAMPLE = ('def calculate_discount(price, discount):\n    return price - (price * discount / 100)\n\n'
          'def get_final_price(price, discount):\n    final = calculate_discount(price, discount)\n    return final_price\n\n'
          'price = 1000\ndiscount = 10\n\n'
          'print("Final Price:", get_final_price(price, discount))\n'
          'print("Average:", sum([10, 20, 30]) / len(numbers))\n')


class ProviderRepairTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='provider-test', password='LongEnough-12345!')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_local_repair_exact_example_executes_in_isolated_runner(self):
        result = LocalRepairEngine.generate_repair(SAMPLE, "NameError: name 'final_price' is not defined")
        self.assertTrue(result['success'])
        with override_settings(EXECUTION_ENABLED=True):
            exit_code, stdout, stderr, _ = PythonRunner.execute(result['repaired_code'])
        self.assertEqual((exit_code, stderr), (0, ''))
        self.assertEqual(stdout.splitlines(), ['Final Price: 900.0', 'Average: 20.0'])

    def test_local_selection_never_calls_external_provider_and_needs_no_consent(self):
        AIProviderSettings.objects.create(user=self.user, mode='local')
        with patch('services.provider_router.RepairEngine._repair_with_gemini', new_callable=AsyncMock) as gemini, patch('services.provider_router.RepairEngine._repair_with_openai', new_callable=AsyncMock) as openai:
            response = self.client.post('/api/v1/repair/', {'source_code': SAMPLE, 'error_message': 'NameError'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['provider'], 'Local Repair Engine')
        gemini.assert_not_awaited()
        openai.assert_not_awaited()

    def test_explicit_gemini_selection_never_calls_openai(self):
        AIProviderSettings.objects.create(user=self.user, mode='gemini')
        with patch('services.provider_router.RepairEngine._repair_with_gemini', new_callable=AsyncMock, return_value={'error': 'Gemini quota exhausted.', 'error_type': 'quota_exhausted', 'source': 'error'}), patch('services.provider_router.RepairEngine._repair_with_openai', new_callable=AsyncMock) as openai:
            response = self.client.post('/api/v1/repair/', {'source_code': SAMPLE, 'error_message': 'NameError', 'allow_external_ai': True}, format='json')
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.data['error_type'], 'quota_exhausted')
        openai.assert_not_awaited()

    def test_provider_preferences_are_authenticated_and_saved(self):
        response = self.client.patch('/api/v1/auth/ai-provider/', {'mode': 'automatic', 'primary_provider': 'gemini', 'secondary_provider': 'openai', 'automatic_fallback': True}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['mode'], 'automatic')
        self.assertTrue(response.data['automatic_fallback'])
