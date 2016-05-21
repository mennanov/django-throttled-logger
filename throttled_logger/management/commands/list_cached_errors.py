from __future__ import unicode_literals

from django.core.cache import cache
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Emit cached log records using a provided log handler.'

    def handle(self, *args, **options):
        errors_registry = cache.get('errors_registry')
        if errors_registry:
            for created_at, error_cache_key in errors_registry:
                subject, message, count = cache.get(error_cache_key)
                self.stdout.write('{created_at} ({count} error{s}): {subject}'.format(
                    created_at=created_at, count=count, s='' if count == 1 else 's', subject=subject))
