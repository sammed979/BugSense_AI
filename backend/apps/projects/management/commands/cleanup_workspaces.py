"""
Django management command to clean up expired project workspaces.
Run: python manage.py cleanup_workspaces
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import os
import shutil
from pathlib import Path


class Command(BaseCommand):
    help = 'Clean up expired project workspaces'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Delete workspaces older than this many days (default: 7)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']

        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"Workspace Cleanup - {'DRY RUN' if dry_run else 'LIVE'}")
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"Removing workspaces older than {days} days")
        self.stdout.write()

        workspace_base = Path(settings.MEDIA_ROOT) / 'project_workspaces'

        if not workspace_base.exists():
            self.stdout.write(self.style.WARNING(f"Workspace directory does not exist: {workspace_base}"))
            return

        cutoff_date = timezone.now() - timedelta(days=days)
        total_size = 0
        deleted_count = 0

        for workspace_dir in workspace_base.iterdir():
            if not workspace_dir.is_dir():
                continue

            # Get directory modification time
            mod_time = timezone.make_timezone_naive(
                timezone.datetime.fromtimestamp(workspace_dir.stat().st_mtime),
                timezone.utc
            )

            if mod_time < cutoff_date:
                # Calculate size
                dir_size = sum(f.stat().st_size for f in workspace_dir.rglob('*') if f.is_file())
                total_size += dir_size
                deleted_count += 1

                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(f"[DRY RUN] Would delete: {workspace_dir.name} ({self.format_size(dir_size)})")
                    )
                else:
                    try:
                        shutil.rmtree(workspace_dir)
                        self.stdout.write(
                            self.style.SUCCESS(f"Deleted: {workspace_dir.name} ({self.format_size(dir_size)})")
                        )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"Failed to delete {workspace_dir.name}: {str(e)}")
                        )

        self.stdout.write()
        self.stdout.write(f"{'='*60}")
        self.stdout.write(f"Summary:")
        self.stdout.write(f"  Workspaces {'would be deleted' if dry_run else 'deleted'}: {deleted_count}")
        self.stdout.write(f"  Total space freed: {self.format_size(total_size)}")
        self.stdout.write(f"{'='*60}")

    def format_size(self, size_bytes):
        """Format bytes to human-readable size."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
