import os
import mock
import sys

from defaults import *
# Import everything from imagescale2, but rename DEF_PORT
# to IMAGESCALE_DEF_PORT
from imagescale2 import *
from imagescale2 import DEF_PORT as IMAGESCALE_DEF_PORT


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(ROOT_DIR, '..', 'database.sqlite3.db'),
        # 'TEST_NAME': os.path.join(ROOT_DIR, '..', 'test_database.sqlite3.db'),
    }
}

JOB_DEFAULT_CLASSIFIER = 'Classifier247'
TWENTYFOUR_DEFAULT_CLASSIFIER = 'SimpleClassifier'

CELERY_RESULT_BACKEND = 'amqp://'
BROKER_URL = 'amqp://'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

JENKINS_TASKS = (
    'django_jenkins.tasks.run_pyflakes',
    'django_jenkins.tasks.run_pep8',
    'django_jenkins.tasks.with_coverage',
    'django_jenkins.tasks.django_tests',
    'django_jenkins.tasks.with_local_celery',
)

try:
    import devserver

    DEVSERVER_MODULES = (
        # 'devserver.modules.sql.SQLRealTimeModule',
        # 'devserver.modules.sql.SQLSummaryModule',
        'devserver.modules.profile.ProfileSummaryModule',

        # Modules not enabled by default
        'devserver.modules.ajax.AjaxDumpModule',
        'devserver.modules.profile.MemoryUseModule',
        'devserver.modules.cache.CacheSummaryModule',
        'devserver.modules.profile.LineProfilerModule',
    )

    DEVSERVER_IGNORED_PREFIXES = ['/__debug__']
    # INSTALLED_APPS = tuple(list(INSTALLED_APPS) + [
    #     'devserver',
    # ])
    # MIDDLEWARE_CLASSES = tuple(list(MIDDLEWARE_CLASSES) + [
    #     'devserver.middleware.DevServerMiddleware',
    # ])
except:
    pass

try:
    import debug_toolbar

    MIDDLEWARE_CLASSES = tuple(list(MIDDLEWARE_CLASSES) + [
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    ])
    INSTALLED_APPS = tuple(list(INSTALLED_APPS) + [
        'debug_toolbar',
    ])
    INTERNAL_IPS = ('127.0.0.1',)
    DEBUG_TOOLBAR_CONFIG = {
        'INTERCEPT_REDIRECTS': False,
    }
except ImportError:
    pass

IMAGESCALE_URL = '127.0.0.1:%d' % IMAGESCALE_DEF_PORT

CELERY_ROUTES = {}
CELERY_REALTIME_QUEUE = CELERY_DEFAULT_QUEUE
CELERY_LONGSCARCE_QUEUE = CELERY_DEFAULT_QUEUE
CELERY_LONGCOMMON_QUEUE = CELERY_DEFAULT_QUEUE

local_settings = os.path.join(os.path.dirname(__file__), 'local.py')
if os.path.isfile(local_settings):
    from local import *

# Mock selenium tests, so that they are not run locally
from django.test import LiveServerTestCase
from urlannotator.main.tests.selenium_tests import *
from urlannotator.crowdsourcing.tests.tagasauris import *
class DummyLiveServerTestCase(LiveServerTestCase):
    pass


def mock_tests(module, prefix, tests):
    mod = sys.modules[module]
    for el in dir(mod):
        if prefix in el:
            mock.patch('%s.%s' % (tests, el), new=DummyLiveServerTestCase).start()

mock_tests(
    module='urlannotator.main.tests.selenium_tests',
    prefix='SeleniumTests',
    tests='urlannotator.main.tests',
)

mock_tests(
    module='urlannotator.crowdsourcing.tests.tagasauris',
    prefix='Tagasauris',
    tests='urlannotator.crowdsourcing.tests',
)
