import random
import string
import multiprocessing
from django.core import signals
from api.settings.production import DATABASES, REST_FRAMEWORK  # noqa
from api.settings.production import *  # noqa


# Fix Django test error.
# https://github.com/django/django/blob/main/django/test/runner.py#L455
# This code was removed in Django > 5.2, so it is safe to remove this when we upgrade.
multiprocessing.set_start_method('fork')
signals.request_started.send = lambda sender, **named: []
signals.request_finished.send = lambda sender, **named: []
signals.got_request_exception.send = lambda sender, **named: []

# A boolean that turns on/off debug mode.
DEBUG = True

# If set to True, Django's normal exception handling of view functions
# will be suppressed, and exceptions will propagate upwards
DEBUG_PROPAGATE_EXCEPTIONS = True

# scheduler for testing
SCHEDULER_MODULE = 'scheduler.mock'
SCHEDULER_URL = 'http://test-scheduler.example.com'

# randomize test database name so we can run multiple unit tests simultaneously
DATABASES['default']['NAME'] = "unittest-{}".format(''.join(
    random.choice(string.ascii_letters + string.digits) for _ in range(8)))
DATABASES['default']['USER'] = 'postgres'

# use locmem cache to isolate the data for each test run
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': DATABASES['default']['NAME'],
        'KEY_PREFIX': DATABASES['default']['NAME'],
    }
}


class DisableMigrations(object):

    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()
