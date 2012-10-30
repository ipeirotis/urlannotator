# Settings file for ci deployment target

import os
from defaults import *
# Import everything from imagescale2, but rename DEF_PORT
# to IMAGESCALE_DEF_PORT
from imagescale2 import *
from imagescale2 import DEF_PORT as IMAGESCALE_DEF_PORT


JOB_DEFAULT_CLASSIFIER = 'Classifier247'
TWENTYFOUR_DEFAULT_CLASSIFIER = 'GooglePredictionClassifier'

SITE_URL = 'devel.urlannotator.10clouds.com'
IMAGESCALE_URL = '%s:%d' % (SITE_URL, IMAGESCALE_DEF_PORT)

EMAIL_BACKEND = 'urlannotator.main.backends.email.EmailBackend'

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


# Broker for celery
BROKER_URL = 'amqp://guest@localhost:5673/'


local_settings = os.path.join(os.path.dirname(__file__), 'local.py')
if os.path.isfile(local_settings):
    from local import *

DATABASES = {
    'default': {
    'ENGINE': 'django.db.backends.postgresql_psycopg2',
    'NAME': DEVEL_DB_NAME,
    'USER': DEVEL_DB_USER,
    'PASSWORD': DEVEL_DB_PASSWORD,
    }
}

# Tagasauris settings
TAGASAURIS_LOGIN = 'urlannotator'
TAGASAURIS_PASS = 'urlannotator'
TAGASAURIS_HOST = 'http://devel.tagasauris.com'
TAGASAURIS_USE_SANDBOX = True

TAGASAURIS_HIT_TYPE = TAGASAURIS_MTURK
TAGASAURIS_HIT_URL = TAGASAURIS_HIT_MTURK_URL

# TODO: This is ugly... any ideas how to change this?
TAGASAURIS_NOTIFY = {
    TAGASAURIS_VOTING_WORKFLOW: 'NotifyTask_1',
    TAGASAURIS_SAMPLE_GATHERER_WORKFLOW: 'NotifyTask_2',
}

TAGASAURIS_CALLBACKS = 'http://devel.urlannotator.10clouds.com'
TAGASAURIS_VOTING_CALLBACK = TAGASAURIS_CALLBACKS +\
    '/api/v1/vote/add/tagasauris/%s/'
TAGASAURIS_BTM_VOTING_CALLBACK = TAGASAURIS_CALLBACKS +\
    '/api/v1/vote/btm/tagasauris/%s/'

TAGASAURIS_VOTE_MEDIA_PER_HIT = 1
TAGASAURIS_VOTE_WORKERS_PER_HIT = 1
XS_SHARING_ALLOWED_ORIGINS = TAGASAURIS_HOST

SOCIAL_AUTH_RAISE_EXCEPTIONS = False
