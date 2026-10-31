from importlib import import_module

from django.db import migrations


def restore_bundled_lessons(apps, schema_editor):
    """Restore the original bundled curriculum if an earlier release removed it."""
    legacy_seed = import_module('apps.learning.migrations.0002_builtin_lessons')
    legacy_seed.seed_lessons(apps, schema_editor)


class Migration(migrations.Migration):
    dependencies = [('learning', '0007_expand_error_catalogue')]
    operations = [migrations.RunPython(restore_bundled_lessons, migrations.RunPython.noop)]
