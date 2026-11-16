from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connections
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    help = 'Log non-sensitive database, user-table, and migration status.'

    def add_arguments(self, parser):
        parser.add_argument('--database', default='default')

    def handle(self, *args, **options):
        connection = connections[options['database']]
        user_model = get_user_model()

        try:
            connection.ensure_connection()
            tables = set(connection.introspection.table_names())
            executor = MigrationExecutor(connection)
            targets = executor.loader.graph.leaf_nodes()
            pending = executor.migration_plan(targets)
            applied_count = len(executor.loader.applied_migrations)
        except DatabaseError:
            self.stderr.write('DATABASE_DIAGNOSTIC status=error reason=database_unavailable')
            raise CommandError(
                'Database diagnostics failed; connection details are omitted.'
            ) from None

        user_table = user_model._meta.db_table
        user_table_exists = user_table in tables
        pending_count = len(pending)
        status = 'ok' if user_table_exists and pending_count == 0 else 'error'

        self.stdout.write(
            'DATABASE_DIAGNOSTIC '
            f'status={status} '
            f'engine={connection.vendor} '
            'connection=ok '
            f'user_model={user_model._meta.label} '
            f'user_table={user_table} '
            f'user_table_exists={str(user_table_exists).lower()} '
            f'migrations_applied={applied_count} '
            f'migrations_pending={pending_count}'
        )

        if status != 'ok':
            raise CommandError('Database schema is incomplete; deployment must not start.')
