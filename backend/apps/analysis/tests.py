from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from apps.dashboard.models import DebuggingSession
from rest_framework.test import APITestCase
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse


class HealthEndpointTests(APITestCase):
    def tearDown(self):
        cache.delete('bugsense_gemini_model_access')
        cache.delete('bugsense_execution_readiness')

    @override_settings(EXECUTION_ENABLED=False)
    @patch('apps.analysis.views.AIService.check_gemini_model_access', return_value={'status': 'reachable', 'ready': True})
    def test_public_health_reports_backend_analyzer_and_provider_without_secret(self, _provider_check):
        response = self.client.get(reverse('ai_provider_health'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['backend']['ready'])
        self.assertTrue(response.data['static_analyzer']['ready'])
        self.assertEqual(response.data['ai']['status'], 'reachable')
        self.assertNotIn('api_key', response.data)


class LogSenseEndpointTests(APITestCase):
    def setUp(self):
        self.url = reverse('logsense_explain')
        self.user = get_user_model().objects.create_user(username='logsense-user', password='safe-test-password-42')
        self.client.force_authenticate(self.user)

    def test_exact_frontend_endpoint_accepts_python_traceback_and_persists_owner_session(self):
        response = self.client.post(self.url, {
            'log': 'Traceback (most recent call last):\n  File "app.py", line 8, in <module>\nNameError: name \'total_price\' is not defined',
            'explanation_level': 'beginner', 'explanation_language': 'en', 'allow_external_ai': False,
        }, format='json')
        self.assertEqual(self.url, '/api/v1/analysis/logsense/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('NameError', response.data['quick_summary'] + str(response.data['line_explanations']))
        session = DebuggingSession.objects.get(id=response.data['session_id'])
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.language, 'technical-log')
        self.assertEqual(session.analyses.count(), 1)

    def test_common_technical_logs_and_informational_logs_return_structured_explanations(self):
        samples = [
            'Page not found (404): /missing/', 'java.lang.NullPointerException at Main.java:14',
            'ReferenceError: userName is not defined', 'MySQL OperationalError: connection refused',
            'npm ERR! code ERESOLVE', 'fatal: not a git repository', 'Docker build failed at step 4',
            'Deployment failed: HTTP 503', 'INFO: service started successfully',
        ]
        for sample in samples:
            with self.subTest(sample=sample):
                response = self.client.post(self.url, {'log': sample}, format='json')
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.data['quick_summary'])
                self.assertTrue(response.data['line_explanations'])
                self.assertIn('root_cause', response.data)

    def test_empty_oversized_invalid_level_and_unsupported_upload_are_rejected(self):
        self.assertEqual(self.client.post(self.url, {'log': '  '}, format='json').status_code, 400)
        self.assertEqual(self.client.post(self.url, {'log': 'x' * 100_001}, format='json').status_code, 413)
        self.assertEqual(self.client.post(self.url, {'log': 'ERROR', 'explanation_level': 'expert'}, format='json').status_code, 400)
        upload = SimpleUploadedFile('source.py', b'print(1)')
        self.assertEqual(self.client.post(self.url, {'file': upload}, format='multipart').status_code, 400)

    def test_txt_and_log_uploads_work_and_endpoint_requires_authentication(self):
        for name in ('trace.txt', 'trace.log'):
            upload = SimpleUploadedFile(name, b'ERROR: connection refused')
            response = self.client.post(self.url, {'file': upload}, format='multipart')
            self.assertEqual(response.status_code, 200)
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.post(self.url, {'log': 'ERROR'}, format='json').status_code, 401)
