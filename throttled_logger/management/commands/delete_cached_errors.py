from __future__ import unicode_literals

from django.core.cache import cache
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Delete all errors from cache. Delete errors registry in cache.'

    def handle(self, *args, **options):
        errors_registry = cache.get('errors_registry')
        if errors_registry:
            for _, error_cache_key in errors_registry:
                cache.delete(error_cache_key)
            cache.delete('errors_registry')
