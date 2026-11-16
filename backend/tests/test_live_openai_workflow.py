"""Opt-in live OpenAI integration test; uses real provider requests."""
import ast
import asyncio
import os
import unittest

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import AIProviderSettings
from services.ai_service import AIService


LIVE_OPENAI_ENABLED = (
    os.environ.get('RUN_LIVE_OPENAI_TESTS', '').strip().lower() == 'true'
    and bool(os.environ.get('OPENAI_API_KEY'))
)


@unittest.skipUnless(LIVE_OPENAI_ENABLED, 'Set RUN_LIVE_OPENAI_TESTS=true and configure OPENAI_API_KEY.')
class LiveOpenAIWorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='live-openai-test',
            password='Test-only-password-123!',
        )
        AIProviderSettings.objects.create(
            user=self.user,
            mode='openai',
            primary_provider='openai',
            secondary_provider='gemini',
            automatic_fallback=False,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_real_openai_explanation_and_repair_endpoint(self):
        source = 'def calculate_total(price, quantity):\n    return price + quantity\n'
        error = 'AssertionError: expected price multiplied by quantity, but the result was their sum.'

        explanation = asyncio.run(
            AIService._analyze_with_openai(
                error,
                '',
                source,
                'python',
            )
        )
        self.assertNotIn('error', explanation)
        self.assertEqual(explanation.get('provider'), 'OpenAI')

        response = self.client.post('/api/v1/repair/', {
            'source_code': source,
            'error_message': error,
            'diagnosis': {'summary': explanation.get('summary', '')},
            'language': 'python',
        }, format='json')

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data.get('provider'), 'OpenAI')
        self.assertNotEqual(response.data.get('repaired_code'), source)
        ast.parse(response.data['repaired_code'])
        self.assertIn('*', response.data['repaired_code'])
