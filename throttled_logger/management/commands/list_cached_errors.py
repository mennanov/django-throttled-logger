from __future__ import unicode_literals

from django.core.cache import cache
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Emit cached errors using a provided log handler.'

    def handle(self, *args, **options):
        errors_registry = cache.get('errors_registry')
        if errors_registry:
            for created_at, error_cache_key in errors_registry:
                error = cache.get(error_cache_key)
                if not error:
                    self.stderr.write('Cache entry for the key "{}" was not found in cache'.format(error_cache_key))
                    continue

                subject, message, count = error
                self.stdout.write('{created_at} ({count} error{s}): {subject}'.format(
                    created_at=created_at, count=count, s='' if count == 1 else 's', subject=subject))
