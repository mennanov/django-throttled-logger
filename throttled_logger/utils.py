from __future__ import unicode_literals

import hashlib
import traceback


def traceback_cache_key(record):
    """Gets a cache key for the given exception info in a LogRecord.

    Args:
        record: logging.LogRecord instance
    Returns:
        str with a cache key or None if no exc_info is given in a LogRecord
    """
    exc_info = record.exc_info
    if exc_info:
        tb_str = ''.join(traceback.format_exception(*exc_info))
        return hashlib.md5(tb_str.encode('utf-8')).hexdigest()
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
