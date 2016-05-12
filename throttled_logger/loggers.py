import hashlib
import logging
from collections import deque

from django.conf import settings
from django.core.cache import cache
from django.utils.log import AdminEmailHandler
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


class CountedAdminEmailHandler(AdminEmailHandler):
    """Appends error counter to the email subject and body."""

    def __init__(self, count, *args, **kwargs):
        super(CountedAdminEmailHandler, self).__init__(*args, **kwargs)
        self.count = count

    def send_mail(self, subject, message, **kwargs):
        counter_msg = '({count}) error{s}'.format(count=self.count, s='' if self.count == 1 else 's')
        super(CountedAdminEmailHandler, self).send_mail(
            '{subject} {msg}'.format(subject=subject, msg=counter_msg),
            '{msg}\n\n{message}'.format(msg=counter_msg, message=message), **kwargs)


def traceback_cache_key(record):
    """Gets a cache key for the given exception info in a LogRecord.

    Args:
        record: logging.LogRecord instance
    Returns:
        str with a cache key or None if no exc_info is given in a LogRecord
    """
    exc_info = record.exc_info
    if exc_info:
        return hashlib.md5(str(exc_info[2])).hexdigest()
    return None


def url_cache_key(record):
    """Gets a cache key for the given url in a LogRecord.

    Args:
        record: logging.LogRecord instance
    Returns:
        str with a cache key
    """
    try:
        url = record.args[0]
    except (IndexError, TypeError):
        return None
    else:
        return url


def exc_type_cache_key(record):
    """Gets a cache key for the given exception type in a LogRecord.

    Args:
        record: logging.LogRecord instance
    Returns:
        str with a cache key or None if no exc_info is given in a LogRecord
    """
    exc_info = record.exc_info
    if exc_info:
        return exc_info[0].__name__
    return None
