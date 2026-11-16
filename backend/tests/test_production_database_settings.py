import os
from pathlib import Path
import subprocess
import sys

from django.test import SimpleTestCase


BACKEND_ROOT = Path(__file__).resolve().parents[1]


class RenderDatabaseSettingsTests(SimpleTestCase):
    def run_settings_check(self, database_url=None):
        env = os.environ.copy()
        env['RENDER'] = 'true'
        env['DEBUG'] = 'True'
        env.pop('DJANGO_DEBUG', None)
        if database_url is None:
            env.pop('DATABASE_URL', None)
        else:
            env['DATABASE_URL'] = database_url

        return subprocess.run(
            [sys.executable, 'manage.py', 'check'],
            cwd=BACKEND_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_render_requires_database_url_even_when_legacy_debug_is_true(self):
        result = self.run_settings_check()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn('DATABASE_URL is required', result.stderr)

    def test_render_rejects_sqlite_database_url(self):
        result = self.run_settings_check('sqlite:///tmp/bugsense.db')

        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Render deployments require DATABASE_URL to use PostgreSQL', result.stderr)
