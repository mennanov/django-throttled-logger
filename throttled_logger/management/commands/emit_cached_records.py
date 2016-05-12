from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Emit cached log records using a provided log handler.'

    def handle(self, *args, **options):
        records_registry = cache.get('records_registry')
        records_to_emit = []
        now = timezone.now()
        while records_registry:
            record_created, cache_key = records_registry[0]
            # Get records old enough to be reported.
            if now - record_created >= settings.THROTTLED_EMAIL_LOGGER_DELAY:
                records_to_emit.append(cache_key)
                records_registry.popleft()
            else:
                break

        for cache_key in records_to_emit:
            record, count = cache.get(cache_key)
            handler = settings.THROTTLED_EMAIL_LOGGER_BACKEND(count)
            handler.emit(record)
            cache.delete(cache_key)

        cache.set('records_registry', records_registry, None)

        self.stdout.write('Emitted {num} record{s}'.format(
            num=len(records_to_emit), s='' if len(records_to_emit) == 1 else 's'))
