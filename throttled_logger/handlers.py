from __future__ import unicode_literals

from collections import deque

from django.conf import settings
from django.core.cache import cache
from django.utils.log import AdminEmailHandler
from django.utils.timezone import now


class CacheHandler(AdminEmailHandler):
    def __init__(self, *args, **kwargs):
        super(CacheHandler, self).__init__(*args, **kwargs)
        self.record = None

    def emit(self, record):
        self.record = record
        super(CacheHandler, self).emit(record)

    def send_mail(self, subject, message, *args, **kwargs):
        # Do not send email: save this message to cache instead.
        cache_key = settings.THROTTLED_EMAIL_LOGGER_CACHE_KEY(self.record)
        if not cache_key:
            # Cache key could not be calculated. Terminate.
            return
        cached_error = cache.get(cache_key)
        if cached_error is None:
            # Create cache for this record: (subject, message, counter).
            cache.set(cache_key, (subject, message, 1), None)
            errors_registry = cache.get('errors_registry', deque())
            errors_registry.append((now(), cache_key))
            # Update cache registry.
            cache.set('errors_registry', errors_registry, None)
        else:
            # Increment a record's counter. Update records subject and message.
            cache.set(cache_key, (subject, message, cached_error[2] + 1), None)
