from __future__ import unicode_literals

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ThrottledLoggerConfig(AppConfig):
    name = 'throttled_logger'
    verbose_name = _('throttled email logger')
