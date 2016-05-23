=====
Django throttled email logger.
=====

Tired of getting to many error emails from Django web site?

This tiny Django app will group and keep all the errors in cache and send them periodically via a cron/Celery task.


Installation
-----------

1. Install via pip from github:
  ```bash
  pip install git+git://github.com/mennanov/django-throttled-logger.git
  ```

2. Add "throttled_logger" to your INSTALLED_APPS setting like this:
  ```python
  
      INSTALLED_APPS = [
          ...
          'throttled_logger',
      ]
  ```
3. Add the following settings to your settings.py:
  ```python
  from datetime import timedelta
  from throttled_logger.utils import traceback_cache_key
  
  # Errors older that this amount of time are periodically sent through a management command (cron/Celery).
  THROTTLED_EMAIL_LOGGER_DELAY = timedelta(minutes=5)
  
  # Callable that gets a LogRecord instance and returns a cache key to group errors by.
  # Available functions: traceback_cache_key, url_cache_key, exc_type_cache_key
  # Feel free to implement your own!
  THROTTLED_EMAIL_LOGGER_CACHE_KEY = traceback_cache_key
  ```
4. Change you ```mail_admins``` handler in ```settings.LOGGING``` to be like this:

  ```python
  LOGGING = {
      'version': 1,
      'handlers': {
          ...
          'mail_admins': {
              'class': 'throttled_logger.handlers.CacheHandler'
          }
      },
      'loggers': {
          ...
          'django': {
              'handlers': ['mail_admins']
          }
      }
  }
  ```


Usage
-----------

* List all errors currently saved in cache (only grouped errors):

  ```bash
  python manage.py list_cached_errors
  ```
* Send all errors that are older than settings.THROTTLED_EMAIL_LOGGER_DELAY via email:

  ```bash
  python manage.py send_cached_errors
  ```

Run tests
----------
  ```bash
  nosetests
  ```
