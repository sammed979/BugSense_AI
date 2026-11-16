from io import StringIO

from django.core.management import call_command
from django.test import TestCase


class HealthEndpointTests(TestCase):
    def test_health_returns_non_sensitive_service_status(self):
        response = self.client.get('/health/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'status': 'ok',
            'service': 'BugSense AI Backend',
        })


class DatabaseDiagnosticsTests(TestCase):
    def test_management_diagnostics_report_only_non_sensitive_status(self):
        output = StringIO()

        call_command('database_diagnostics', stdout=output)

        details = output.getvalue()
        self.assertIn('engine=', details)
        self.assertIn('user_model=auth.User', details)
        self.assertIn('user_table=auth_user', details)
        self.assertIn('user_table_exists=true', details)
        self.assertIn('migrations_pending=0', details)
        self.assertNotIn('password', details.lower())
        self.assertNotIn('database_url', details.lower())
