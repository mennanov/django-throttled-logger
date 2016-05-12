import hashlib
import logging
from collections import deque
from datetime import datetime, timedelta

import django
import mock
from django.conf import settings
from django.core import management
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from . import loggers

default_settings = dict(
    THROTTLED_EMAIL_LOGGER_DELAY=timedelta(minutes=5),
    THROTTLED_EMAIL_LOGGER_BACKEND=loggers.CountedAdminEmailHandler,
    THROTTLED_EMAIL_LOGGER_CACHE_KEY=loggers.traceback_cache_key,
    INSTALLED_APPS=['throttled_logger'],
)

settings.configure(**default_settings)
django.setup()


class CacheHandlerTest(SimpleTestCase):
    def setUp(self):
        super(CacheHandlerTest, self).setUp()
        exception = ValueError('Error message')
        self.exc_info = (type(exception), exception, 'Traceback')
        self.record = logging.makeLogRecord(
            {'name': 'logger name', 'level': 'ERROR', 'pathname': '/path/to/file.py', 'msg': 'Error message',
             'exc_info': self.exc_info, 'func': 'func'}
        )

    def tearDown(self):
        super(CacheHandlerTest, self).tearDown()
        # Make sure cache is fully cleared after each test case.
        cache.clear()

    def test_saves_log_record_into_cache(self):
        handler = loggers.CacheHandler()
        handler.emit(self.record)
        record, counter = cache.get(settings.THROTTLED_EMAIL_LOGGER_CACHE_KEY(self.record))
        self.assertEqual(record.exc_info[0], self.record.exc_info[0])
        self.assertEqual(1, counter)

    def test_populates_cache_records_registry(self):
        handler = loggers.CacheHandler()
        handler.emit(self.record)
        records_registry = cache.get('records_registry')
        cache_key = settings.THROTTLED_EMAIL_LOGGER_CACHE_KEY(self.record)
        self.assertIn(cache_key, {key for _, key in records_registry})

    def test_increments_record_cache_counter(self):
        handler = loggers.CacheHandler()
        for _ in range(5):
            handler.emit(self.record)
        record, counter = cache.get(settings.THROTTLED_EMAIL_LOGGER_CACHE_KEY(self.record))
        self.assertEqual(counter, 5)

    def test_multiple_emits_of_the_same_record_dont_populate_records_registry_cache(self):
        handler = loggers.CacheHandler()
        for _ in range(5):
            handler.emit(self.record)
        records_registry = cache.get('records_registry')
        self.assertEqual(1, len(records_registry))

    @override_settings(THROTTLED_EMAIL_LOGGER_CACHE_KEY=lambda x: None)
    def test_terminates_if_no_cachekey(self):
        handler = loggers.CacheHandler()
        handler.emit(self.record)
        self.assertFalse(cache._cache)


class TracebackCacheKeyTest(SimpleTestCase):
    def setUp(self):
        super(TracebackCacheKeyTest, self).setUp()
        exception = ValueError('Error message')
        self.exc_info = [type(exception), exception, 'Traceback']
        self.record = logging.makeLogRecord({'exc_info': self.exc_info})

    def test_returns_traceback_hash(self):
        cache_key = loggers.traceback_cache_key(self.record)
        self.assertEqual(hashlib.md5('Traceback').hexdigest(), cache_key)

    def test_returns_none_if_no_exception(self):
        self.record.exc_info = None
        cache_key = loggers.traceback_cache_key(self.record)
        self.assertIsNone(cache_key)


class URLCacheKeyTest(SimpleTestCase):
    def setUp(self):
        super(URLCacheKeyTest, self).setUp()
        self.record = logging.makeLogRecord({'args': ('/test/',)})

    def test_returns_url(self):
        cache_key = loggers.url_cache_key(self.record)
        self.assertEqual('/test/', cache_key)

    def test_returns_none_if_no_args(self):
        self.record.args = None
        cache_key = loggers.url_cache_key(self.record)
        self.assertIsNone(cache_key)


class ExcTypeCacheKeyTest(SimpleTestCase):
    def setUp(self):
        super(ExcTypeCacheKeyTest, self).setUp()
        exception = ValueError('Error message')
        self.exc_info = [type(exception), exception, 'Traceback']
        self.record = logging.makeLogRecord({'exc_info': self.exc_info})

    def test_returns_exception_type(self):
        cache_key = loggers.exc_type_cache_key(self.record)
        self.assertEqual('ValueError', cache_key)

    def test_returns_none_if_exception(self):
        self.record.exc_info = None
        cache_key = loggers.exc_type_cache_key(self.record)
        self.assertIsNone(cache_key)


class EmitCachedRecords(SimpleTestCase):
    def tearDown(self):
        super(EmitCachedRecords, self).tearDown()
        # Make sure cache is fully cleared after each test case.
        cache.clear()

    @override_settings(THROTTLED_EMAIL_LOGGER_BACKEND=mock.MagicMock())
    def test_emits_records(self):
        now = datetime.now()
        delay = settings.THROTTLED_EMAIL_LOGGER_DELAY
        records_registry = deque([
            (now - (delay + timedelta(seconds=60)), 'record1'),
            (now - (delay + timedelta(seconds=30)), 'record2')
        ])
        cache.set('records_registry', records_registry, None)
        exception1 = ValueError('Error message')
        exc_info1 = (type(exception1), exception1, 'Traceback')
        record1 = logging.makeLogRecord(
            {'name': 'record1', 'level': 'ERROR', 'pathname': '/path/to/file.py', 'msg': 'Error message',
             'exc_info': exc_info1, 'func': 'func'}
        )
        cache.set('record1', (record1, 5))

        exception2 = IndexError('Error message')
        exc_info2 = (type(exception1), exception2, 'Traceback')
        record2 = logging.makeLogRecord(
            {'name': 'record2', 'level': 'ERROR', 'pathname': '/path/to/file.py', 'msg': 'Error message',
             'exc_info': exc_info2, 'func': 'func'}
        )
        cache.set('record2', (record2, 10))

        management.call_command('emit_cached_records')
        # Ensure that all records were emitted.
        self.assertEqual(2, settings.THROTTLED_EMAIL_LOGGER_BACKEND.call_count)

    @override_settings(THROTTLED_EMAIL_LOGGER_BACKEND=mock.MagicMock())
    def test_emits_only_old_records(self):
        now = datetime.now()
        delay = settings.THROTTLED_EMAIL_LOGGER_DELAY
        records_registry = deque([
            (now - (delay + timedelta(seconds=60)), 'record1'),
            (now - timedelta(seconds=30), 'record2')
        ])
        cache.set('records_registry', records_registry, None)
        exception1 = ValueError('Error message')
        exc_info1 = (type(exception1), exception1, 'Traceback')
        record1 = logging.makeLogRecord(
            {'name': 'record1', 'level': 'ERROR', 'msg': 'Error message',
             'exc_info': exc_info1, 'func': 'func'}
        )
        cache.set('record1', (record1, 5))

        management.call_command('emit_cached_records')
        # Ensure that only old record was emitted.
        self.assertEqual(1, settings.THROTTLED_EMAIL_LOGGER_BACKEND.call_count)
        # Check that records registry is reduced.
        records_registry = cache.get('records_registry')
        self.assertEqual(1, len(records_registry))
        self.assertNotIn('record1', {k for _, k in records_registry})
