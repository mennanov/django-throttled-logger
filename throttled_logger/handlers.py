from __future__ import unicode_literals

import logging
from collections import deque

from django.conf import settings
from django.core.cache import cache
from django.utils.timezone import now


class CacheHandler(logging.Handler):
    def emit(self, record):
        cache_key = settings.THROTTLED_EMAIL_LOGGER_CACHE_KEY(record)
        if not cache_key:
            # Cache key could not be calculated. Terminate.
            return

        cached_record = cache.get(cache_key)
        if cached_record is None:
            # Create cache for this record: (record, counter).
            cache.set(cache_key, (record, 1))
            records_registry = cache.get('records_registry', deque())
            records_registry.append((now(), cache_key))
            # Update cache registry.
            cache.set('records_registry', records_registry, None)
        else:
            # Increment a record's counter.
            cache.set(cache_key, (cached_record[0], cached_record[1] + 1), None)
