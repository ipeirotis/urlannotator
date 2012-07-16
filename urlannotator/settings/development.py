import os
from defaults import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(ROOT_DIR, '..', 'database.sqlite3.db'),
    }
}

#EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_BACKEND = 'urlannotator.main.backends.email.EmailBackend'

JENKINS_TASKS = (
    'django_jenkins.tasks.run_pyflakes',
    'django_jenkins.tasks.run_pep8',
    'django_jenkins.tasks.with_coverage',
    'django_jenkins.tasks.django_tests',
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

local_settings = os.path.join(os.path.dirname(__file__), 'local.py')
if os.path.isfile(local_settings):
    from local import *

# Broker for celery
# WARN: Do not use the amqp backend with SQS.
BROKER_URL = 'sqs://%s:%s@' % (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

# Do we need this config?
BROKER_TRANSPORT_OPTIONS = {
    'region': 'eu-west-1',
    # 'visibility_timeout': 3600,
    # 'polling_interval': 0.3,
    'queue_name_prefix': 'urlannotator-',
}

# Celery database backend
# By default celery stores state in django db.
# CELERY_RESULT_BACKEND = "database"
# CELERY_RESULT_DBURI = "sqlite:///celerydb.sqlite"
# CELERY_RESULT_DBURI = "mysql://scott:tiger@localhost/foo"

# We can ignore results from celery tasks (no need for db backend)
# We can also do this by: @celery.task(ignore_result=True)
# CELERY_IGNORE_RESULT = True
