from __future__ import unicode_literals

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Emit cached log records using a provided log handler.'

    def handle(self, *args, **options):
        errors_registry = cache.get('errors_registry')
        errors_to_emit = []
        now = timezone.now()
        while errors_registry:
            error_created, cache_key = errors_registry[0]
            # Get errors old enough to be reported.
            if now - error_created >= settings.THROTTLED_EMAIL_LOGGER_DELAY:
                errors_to_emit.append(cache_key)
                errors_registry.popleft()
            else:
                break

        sent = 0
        for cache_key in errors_to_emit:
            subject, message, count = cache.get(cache_key)
            counter_msg = '({count} error{s})'.format(count=count, s='' if count == 1 else 's')
            mail.mail_admins('{subject} {msg}'.format(subject=subject, msg=counter_msg),
                             '{msg}\n\n{message}'.format(msg=counter_msg, message=message))
            cache.delete(cache_key)
            sent += 1

        cache.set('errors_registry', errors_registry, None)

        self.stdout.write('{num} error{s} sent'.format(
            num=sent, s='' if len(errors_to_emit) == 1 else 's'))
