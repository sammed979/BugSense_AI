from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connections


POSTGRES_MIGRATION_LOCK = 0x42554753454E5345


class Command(BaseCommand):
    help = 'Apply migrations while serializing PostgreSQL deploy instances.'

    def add_arguments(self, parser):
        parser.add_argument('--database', default='default')
        parser.add_argument('--noinput', '--no-input', action='store_false', dest='interactive')
        parser.set_defaults(interactive=True)

    def handle(self, *args, **options):
        alias = options['database']
        connection = connections[alias]
        migrate_options = {
            'database': alias,
            'interactive': options['interactive'],
            'verbosity': options['verbosity'],
        }

        try:
            connection.ensure_connection()
        except DatabaseError:
            raise CommandError(
                'Database connection failed; connection details are omitted.'
            ) from None

        if connection.vendor != 'postgresql':
            if not settings.DEBUG:
                raise CommandError('Production migrations require PostgreSQL.')
            call_command('migrate', **migrate_options)
            return

        lock_acquired = False
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_lock(%s)', [POSTGRES_MIGRATION_LOCK])
                lock_acquired = True
            self.stdout.write('DATABASE_MIGRATION_LOCK acquired')
            call_command('migrate', **migrate_options)
        finally:
            if lock_acquired:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT pg_advisory_unlock(%s)', [POSTGRES_MIGRATION_LOCK])
                self.stdout.write('DATABASE_MIGRATION_LOCK released')
