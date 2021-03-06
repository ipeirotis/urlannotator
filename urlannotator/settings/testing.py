import os

from defaults import *
# Import everything from imagescale2, but rename DEF_PORT
# to IMAGESCALE_DEF_PORT
from imagescale2 import *
from imagescale2 import DEF_PORT as IMAGESCALE_DEF_PORT


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(ROOT_DIR, '..', 'database.sqlite3.db'),
        'TEST_NAME': os.path.join(ROOT_DIR, '..', 'test_database.sqlite3.db'),
    }
}

JOB_DEFAULT_CLASSIFIER = 'Classifier247'
TWENTYFOUR_DEFAULT_CLASSIFIER = 'SimpleClassifier'

CELERY_RESULT_BACKEND = 'amqp://'
BROKER_URL = 'amqp://'

SITE_URL = 'devel.urlannotator.10clouds.com'
POSIX_PREFIX = 'testing'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

JENKINS_TASKS = (
    'django_jenkins.tasks.run_pyflakes',
    'django_jenkins.tasks.run_pep8',
    'django_jenkins.tasks.with_coverage',
    'django_jenkins.tasks.django_tests',
    'django_jenkins.tasks.with_local_celery',
)

# Don't use memcache in testing
CACHES['memcache']['BACKEND'] = 'django.core.cache.backends.dummy.DummyCache'

try:
    import devserver

    DEVSERVER_MODULES = (
        'devserver.modules.sql.SQLRealTimeModule',
        'devserver.modules.sql.SQLSummaryModule',
        'devserver.modules.profile.ProfileSummaryModule',

        # Modules not enabled by default
        'devserver.modules.ajax.AjaxDumpModule',
        'devserver.modules.profile.MemoryUseModule',
        'devserver.modules.cache.CacheSummaryModule',
        'devserver.modules.profile.LineProfilerModule',
    )

    DEVSERVER_IGNORED_PREFIXES = ['/__debug__']
    INSTALLED_APPS = tuple(list(INSTALLED_APPS) + [
        'devserver',
    ])
    MIDDLEWARE_CLASSES = tuple(list(MIDDLEWARE_CLASSES) + [
        'devserver.middleware.DevServerMiddleware'
    ])
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

LOGGING['loggers'] = {}

ODESK_TEAM_PREFIX = 'testing'

local_settings = os.path.join(os.path.dirname(__file__), 'local.py')
if os.path.isfile(local_settings):
    from local import *

# Tagasauris settings
# NOTE: This settings are used also for testing tagasauris integration. Many
# jobs are created on Tagasauris side so devel.tagasauris.com should be used
# ALWAYS.
TAGASAURIS_HOST = 'http://devel.tagasauris.com'
TAGASAURIS_HIT_URL = TAGASAURIS_HOST + '/actions/start_annotation/?hid=%s'

ODESK_HIT_TYPE = TAGASAURIS_SOCIAL
OWN_WORKFORCE_HIT_TYPE = TAGASAURIS_SOCIAL

XS_SHARING_ALLOWED_ORIGINS = TAGASAURIS_HOST
XS_SHARING_ALLOWED_METHODS = ['POST', 'GET']
