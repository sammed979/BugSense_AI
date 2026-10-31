from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase
from unittest.mock import patch

from apps.dashboard.models import DebuggingSession


class ExecutionSessionTests(APITestCase):
    @override_settings(EXECUTION_ENABLED=True)
    @patch('sandbox.python_runner.PythonRunner.execute', return_value=(1, '', "NameError: name 'total_price' is not defined", 4.2))
    def test_execution_stores_code_and_returns_session_for_history(self, _execute):
        user = get_user_model().objects.create_user(username='runner-user', password='safe-test-password-42')
        self.client.force_authenticate(user)
        response = self.client.post('/api/v1/execution/execute/', {
            'source_code': 'print(total_price)', 'language': 'python',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['session_id'])
        session = DebuggingSession.objects.get(id=response.data['session_id'], user=user)
        self.assertEqual(session.source_code, 'print(total_price)')
        self.assertIn('NameError', session.terminal_logs)

    @override_settings(EXECUTION_ENABLED=False)
    def test_disabled_runner_reports_unavailable_but_keeps_the_session(self):
        user = get_user_model().objects.create_user(username='disabled-runner', password='safe-test-password-42')
        self.client.force_authenticate(user)
        response = self.client.post('/api/v1/execution/execute/', {
            'source_code': 'print(500)', 'language': 'python',
        }, format='json')
        self.assertEqual(response.status_code, 503)
        session = DebuggingSession.objects.get(id=response.data['session_id'], user=user)
        self.assertEqual(session.source_code, 'print(500)')
        self.assertEqual(session.status, 'EXECUTION_UNAVAILABLE')

    @override_settings(EXECUTION_ENABLED=True)
    def test_nameerror_debugging_pipeline_and_history_reopen(self):
        user = get_user_model().objects.create_user(username='pipeline-user', password='safe-test-password-42')
        self.client.force_authenticate(user)
        original = (
            'def calculate_total(price, quantity):\n'
            '    total = price * quantity\n'
            '    return total\n\n'
            'price = 100\nquantity = 5\nprint(total_price)'
        )

        failed_run = self.client.post('/api/v1/execution/execute/', {
            'source_code': original, 'language': 'python',
        }, format='json')
        self.assertEqual(failed_run.status_code, 200)
        self.assertEqual(failed_run.data['exit_code'], 1)
        self.assertIn("NameError: name 'total_price' is not defined", failed_run.data['stderr'])
        session_id = failed_run.data['session_id']

        analysis = self.client.post('/api/v1/analysis/analyze/', {
            'source_code': original,
            'language': 'python',
            'error_message': failed_run.data['stderr'],
            'terminal_logs': failed_run.data['stderr'],
            'session_id': session_id,
            'allow_external_ai': False,
        }, format='json')
        self.assertEqual(analysis.status_code, 200)
        self.assertEqual(analysis.data['runtime_diagnosis']['error_category'], 'NameError')

        proposal = self.client.post('/api/v1/repair/', {
            'source_code': original,
            'language': 'python',
            'error_message': failed_run.data['stderr'],
            'session_id': session_id,
            'use_heuristic': True,
        }, format='json')
        self.assertEqual(proposal.status_code, 200)
        self.assertEqual(proposal.data['source'], 'heuristic')
        self.assertIn('print(calculate_total(price, quantity))', proposal.data['repaired_code'])
        self.assertNotEqual(proposal.data['repaired_code'], original)

        # Simulate user approval by submitting the candidate only after reviewing the proposal.
        verified = self.client.post('/api/v1/execution/execute/', {
            'source_code': proposal.data['repaired_code'],
            'language': 'python',
            'session_id': session_id,
        }, format='json')
        self.assertEqual(verified.status_code, 200)
        self.assertEqual(verified.data['exit_code'], 0)
        self.assertEqual(verified.data['stdout'].strip(), '500')

        history = self.client.get('/api/v1/history/')
        self.assertEqual(history.status_code, 200)
        self.assertTrue(any(str(item['id']) == str(session_id) for item in history.data['sessions']))
        reopened = self.client.get(f'/api/v1/history/sessions/{session_id}/')
        self.assertEqual(reopened.status_code, 200)
        self.assertEqual(reopened.data['source_code'], proposal.data['repaired_code'])
