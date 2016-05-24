from __future__ import unicode_literals

import logging
import sys
from collections import deque
from datetime import datetime, timedelta

import django
import mock
from django.conf import settings
from django.core import mail
from django.test import SimpleTestCase, override_settings

from . import utils

default_settings = dict(
    THROTTLED_EMAIL_LOGGER_DELAY=timedelta(minutes=5),
    THROTTLED_EMAIL_LOGGER_CACHE_KEY=utils.traceback_cache_key,
    INSTALLED_APPS=['throttled_logger'],
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    ADMINS=[('admin', 'admin@example.com')]
)

settings.configure(**default_settings)
django.setup()

# Must be imported only after settings are already configured.
from django.core import management
from django.core.cache import cache

from . import handlers


class CacheHandlerTest(SimpleTestCase):
    def setUp(self):
        super(CacheHandlerTest, self).setUp()
        try:
            raise ValueError('Error message')
        except ValueError:
            self.exc_info = sys.exc_info()
            self.record = logging.makeLogRecord(
                {'name': 'logger name', 'level': 'ERROR', 'pathname': '/path/to/file.py', 'msg': 'Error message',
                 'exc_info': self.exc_info, 'func': 'func'}
            )
            self.handler = handlers.CacheHandler()
            self.handler.record = self.record

    def tearDown(self):
        super(CacheHandlerTest, self).tearDown()
        # Make sure cache is fully cleared after each test case.
        cache.clear()

    def test_send_mail_saves_message_into_cache(self):
        self.handler.send_mail('subject', 'message')
        error = cache.get(settings.THROTTLED_EMAIL_LOGGER_CACHE_KEY(self.record))
        self.assertEqual(('subject', 'message', 1), error)

    def test_send_mail_increments_error_cache_counter(self):
        for _ in range(5):
            self.handler.send_mail('subject', 'message')
        _, _, counter = cache.get(settings.THROTTLED_EMAIL_LOGGER_CACHE_KEY(self.record))
        self.assertEqual(counter, 5)

    def test_multiple_emits_of_the_same_record_dont_populate_records_registry_cache(self):
        for _ in range(5):
            self.handler.send_mail('subject', 'message')
        errors_registry = cache.get('errors_registry')
        self.assertEqual(1, len(errors_registry))

    @override_settings(THROTTLED_EMAIL_LOGGER_CACHE_KEY=lambda x: None)
    def test_send_mail_terminates_if_no_cachekey(self):
        self.handler.send_mail('subject', 'message')
        # LocMem cache backend is assumed here.
        self.assertFalse(cache._cache)

    def test_emit_does_not_call_django_send_mail(self):
        try:
            raise Exception('test exception')
        except:
            record = mock.MagicMock()
            record.exc_info = sys.exc_info()
            self.handler.emit(record)
            self.assertEqual(0, len(mail.outbox), 'Django < 1.8 is not supported.')


class TracebackCacheKeyTest(SimpleTestCase):
    def setUp(self):
        super(TracebackCacheKeyTest, self).setUp()
        try:
            raise ValueError('Error message')
        except ValueError:
            self.exc_info = sys.exc_info()
            self.record = logging.makeLogRecord({'exc_info': self.exc_info})

    def test_returns_same_hash_for_same_traceback(self):
        # Check that hashing function is stable.
        cache_key1 = utils.traceback_cache_key(self.record)
        cache_key2 = utils.traceback_cache_key(self.record)
        self.assertEqual(cache_key1, cache_key2)

    def test_returns_none_if_no_exception(self):
        self.record.exc_info = None
        cache_key = utils.traceback_cache_key(self.record)
        self.assertIsNone(cache_key)

    def test_returns_different_keys_for_different_tracebacks(self):
        value_error_cache_key = utils.traceback_cache_key(self.record)
        try:
            raise LookupError('test')
        except LookupError:
            self.record.exc_info = sys.exc_info()
            lookup_error_cache_key = utils.traceback_cache_key(self.record)
            self.assertNotEqual(value_error_cache_key, lookup_error_cache_key)


class URLCacheKeyTest(SimpleTestCase):
    def setUp(self):
        super(URLCacheKeyTest, self).setUp()
        self.record = logging.makeLogRecord({'args': ('/test/',)})

    def test_returns_url(self):
        cache_key = utils.url_cache_key(self.record)
        self.assertEqual('/test/', cache_key)

    def test_returns_none_if_no_args(self):
        self.record.args = None
        cache_key = utils.url_cache_key(self.record)
        self.assertIsNone(cache_key)


class ExcTypeCacheKeyTest(SimpleTestCase):
    def setUp(self):
        super(ExcTypeCacheKeyTest, self).setUp()
        exception = ValueError('Error message')
        self.exc_info = [type(exception), exception, 'Traceback']
        self.record = logging.makeLogRecord({'exc_info': self.exc_info})

    def test_returns_exception_type(self):
        cache_key = utils.exc_type_cache_key(self.record)
        self.assertEqual('ValueError', cache_key)

    def test_returns_none_if_exception(self):
        self.record.exc_info = None
        cache_key = utils.exc_type_cache_key(self.record)
        self.assertIsNone(cache_key)


class SendCachedErrors(SimpleTestCase):
    def tearDown(self):
        super(SendCachedErrors, self).tearDown()
        # Make sure cache is fully cleared after each test case.
        cache.clear()

    def test_send_emails_with_errors(self):
        now = datetime.now()
        delay = settings.THROTTLED_EMAIL_LOGGER_DELAY
        errors_registry = deque([
            (now - (delay + timedelta(seconds=60)), 'error1_key'),
            (now - (delay + timedelta(seconds=30)), 'error2_key')
        ])
        cache.set('errors_registry', errors_registry, None)
        cache.set('error1_key', ('subject 1', 'message 1', 5))
        cache.set('error2_key', ('subject 2', 'message 2', 10))

        management.call_command('send_cached_errors')
        # Ensure that all errors were emitted.
        self.assertEqual(2, len(mail.outbox))
        # Ensure that errors are deleted from cache.
        self.assertIsNone(cache.get('error1_key'))
        self.assertIsNone(cache.get('error2_key'))
        # Ensure that errors registry is empty.
        self.assertEqual(0, len(cache.get('errors_registry')))

    def test_emits_only_old_records(self):
        now = datetime.now()
        delay = settings.THROTTLED_EMAIL_LOGGER_DELAY
        errors_registry = deque([
            (now - (delay + timedelta(seconds=60)), 'error1_key'),
            (now - timedelta(seconds=30), 'error2_key')
        ])
        cache.set('errors_registry', errors_registry, None)
        cache.set('error1_key', ('subject 1', 'message 1', 5))

        management.call_command('send_cached_errors')
        # Ensure that only old record was emitted.
        self.assertEqual(1, len(mail.outbox))
        # Check that records registry is reduced.
        errors_registry = cache.get('errors_registry')
        self.assertEqual(1, len(errors_registry))
        self.assertNotIn({'error2_key'}, {k for _, k in errors_registry})
