import datetime
import os
import tempfile
import sys
from django.core.urlresolvers import reverse_lazy

DEBUG = not 'celery' in sys.argv
TEMPLATE_DEBUG = DEBUG
JS_DEBUG = DEBUG

_tempdir = tempfile.tempdir or '/tmp'
ROOT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

ADMINS = ()
MANAGERS = ADMINS
DATABASES = {}

TIME_ZONE = 'Europe/Warsaw'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = True
USE_L10N = True
USE_TZ = True

MEDIA_ROOT = ''
MEDIA_URL = ''
STATIC_ROOT = os.path.join(ROOT_DIR, '..', 'collected_static')

EMAIL_HOST = ''
EMAIL_PORT = '587'
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS = True

STATIC_URL = '/statics/'

# Default classifier used for NEW jobs. Has to be a valid class name from
# urlannotator.classification.classifiers module
JOB_DEFAULT_CLASSIFIER = 'Classifier247'
TWENTYFOUR_DEFAULT_CLASSIFIER = 'GooglePredictionClassifier'

SOCIAL_AUTH_CREATE_USERS = False

SOCIAL_AUTH_PIPELINE = (
    'social_auth.backends.pipeline.social.social_auth_user',
    'urlannotator.main.backends.pipeline.create_user',
    'social_auth.backends.pipeline.social.associate_user',
    'social_auth.backends.pipeline.social.load_extra_data',
    'social_auth.backends.pipeline.user.update_user_details',
)

LOGIN_URL = reverse_lazy('login')
LOGIN_REDIRECT_URL = reverse_lazy('index')


# Defininig directory for 10clouds commons
def _tenclouds_directory():
    import tenclouds
    return os.path.abspath(os.path.dirname(os.path.dirname(tenclouds.__file__)))

# Additional locations of static files
STATICFILES_DIRS = (
    os.path.join(ROOT_DIR, 'statics'),
    _tenclouds_directory(),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder'
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = ''

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'urlannotator.main.middlewares.crossdomainxhr.XsSharing',
)

AUTHENTICATION_BACKENDS = (
    'social_auth.backends.twitter.TwitterBackend',
    'social_auth.backends.facebook.FacebookBackend',
    'social_auth.backends.google.GoogleOAuth2Backend',
    'django.contrib.auth.backends.ModelBackend',
)

ROOT_URLCONF = 'urlannotator.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'urlannotator.wsgi.application'

TEMPLATE_CONTEXT_PROCESSORS = (
  'django.contrib.auth.context_processors.auth',
  'django.core.context_processors.debug',
  'django.core.context_processors.i18n',
  'django.core.context_processors.media',
  'django.core.context_processors.static',
  'django.core.context_processors.tz',
  'django.contrib.messages.context_processors.messages'
)

TEMPLATE_DIRS = (
    'templates',
    os.path.join(ROOT_DIR, 'templates'),
)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': os.path.join(_tempdir, 'urlannotator__file_based_cache'),
    }
}
#SESSION_ENGINE = 'django.contrib.sessions.backends.cache'

BASE_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.markup',

    'pipeline',
    'south',
    'django_jenkins',
    'bootstrap',
    'djcelery',
    'tastypie',

    'social_auth',
    'odesk',
)

PROJECT_APPS = (
    'urlannotator.classification',
    'urlannotator.crowdsourcing',
    'urlannotator.flow_control',
    'urlannotator.main',
    'urlannotator.tools',
    'urlannotator.statistics',
    'urlannotator.logging',
)

INSTALLED_APPS = BASE_APPS + PROJECT_APPS

SOCIAL_AUTH_PROTECTED_USER_FIELDS = ['email', 'username']
SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/'
SOCIAL_AUTH_NEW_USER_REDIRECT_URL = '/settings/'
SOCIAL_AUTH_NEW_ASSOCIATION_REDIRECT_URL = '/settings/'
SOCIAL_AUTH_DISCONNECT_REDIRECT_URL = '/settings/'
LOGIN_REDIRECT_URL = ''
LOGIN_URL = '/login/'
AUTH_PROFILE_MODULE = 'main.Account'
SOUTH_TESTS_MIGRATE = False

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

try:
    from pipeline_js import PIPELINE_JS as _pipeline_js
    from pipeline_css import PIPELINE_CSS as _pipeline_css
    # two pylint warnings less:
    PIPELINE_JS = _pipeline_js
    PIPELINE_CSS = _pipeline_css
except ImportError:
    pass


PIPELINE = not DEBUG
if PIPELINE:
    STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'

PIPELINE_COMPILERS = (
    'pipeline.compilers.coffee.CoffeeScriptCompiler',
    'pipeline.compilers.less.LessCompiler',
)
PIPELINE_LESS_BINARY = 'lessc'
PIPELINE_YUI_BINARY = os.path.join(ROOT_DIR, '..', 'bin', 'yuicompressor.sh')
PIPELINE_COFFEE_SCRIPT_BINARY = os.path.join(ROOT_DIR, '..', 'bin', 'coffeefinder.sh')

PIPELINE_TEMPLATE_FUNC = 'new EJS'
PIPELINE_TEMPLATE_NAMESPACE = 'window.Template'
PIPELINE_TEMPLATE_EXT = '.ejs'

# Celery
# FIXME: there is issue with admin monitor:
# http://stackoverflow.com/questions/8744953/why-doesnt-celerycam-work-with-amazon-sqs?rq=1
import djcelery
djcelery.setup_loader()

# Celery tasks. INSTALLED_APPS also will be scanned so this is optional.
CELERY_IMPORTS = (
    'urlannotator.flow_control.event_system',
    'urlannotator.flow_control.event_handlers',
    'urlannotator.main.event_handlers',
    'urlannotator.statistics.monitor_tasks',
)

# Respawn a worker after 10 tasks done. Memory leaks shall not prevail!
CELERYD_MAX_TASKS_PER_CHILD = 10
CELERY_MAX_CACHED_RESULTS = 5

# Interval between a job monitor check. Defaults to 15 minutes.
JOB_MONITOR_INTERVAL = datetime.timedelta(seconds=15 * 60)
WORKER_MONITOR_INTERVAL = datetime.timedelta(seconds=15 * 60)

# Interval between statistics entries, to store a new one.
JOB_MONITOR_ENTRY_INTERVAL = datetime.timedelta(hours=1)

CELERYBEAT_SCHEDULE = {
    'spent_monitor': {
        'task': 'urlannotator.statistics.monitor_tasks.SpentMonitor',
        'schedule': JOB_MONITOR_INTERVAL,
        'kwargs': {'interval': JOB_MONITOR_ENTRY_INTERVAL},
    },
    'url_monitor': {
        'task': 'urlannotator.statistics.monitor_tasks.URLMonitor',
        'schedule': JOB_MONITOR_INTERVAL,
        'kwargs': {'interval': JOB_MONITOR_ENTRY_INTERVAL},
    },
    'progress_monitor': {
        'task': 'urlannotator.statistics.monitor_tasks.ProgressMonitor',
        'schedule': JOB_MONITOR_INTERVAL,
        'kwargs': {'interval': JOB_MONITOR_ENTRY_INTERVAL},
    },
    'links_monitor': {
        'task': 'urlannotator.statistics.monitor_tasks.LinksMonitor',
        'schedule': WORKER_MONITOR_INTERVAL,
        'kwargs': {'interval': datetime.timedelta(days=1)}
    },
    'send_validated_samples': {
        'task': 'urlannotator.classification.event_handlers.SampleVotingManager',
        'schedule': datetime.timedelta(seconds=3 * 60),
        'args': []
    },
    'process_votes': {
        'task': 'urlannotator.classification.event_handlers.ProcessVotesManager',
        'schedule': datetime.timedelta(seconds=3 * 60),
        'args': []
    },

}

# Test runner
# CELERY_ALWAYS_EAGER = True
TEST_RUNNER = 'djcelery.contrib.test_runner.CeleryTestSuiteRunner'

# Tagasauris integretion settings
TAGASAURIS_LOGIN = 'urlannotator'
TAGASAURIS_PASS = 'urlannotator'
TAGASAURIS_HOST = 'http://devel.tagasauris.com'
TAGASAURIS_USE_SANDBOX = True

TAGASAURIS_HIT_SOCIAL_URL = TAGASAURIS_HOST + '/actions/start_annotation/?hid=%s'
TAGASAURIS_HIT_SANDBOX_URL = "https://workersandbox.mturk.com/mturk/preview?groupId=%s"
TAGASAURIS_HIT_MTURK_URL = "https://mturk.com/mturk/preview?groupId=%s"

TAGASAURIS_HIT_URL = TAGASAURIS_HIT_SANDBOX_URL

TAGASAURIS_HIT_TYPE = 'mturk'

TAGASAURIS_SAMPLE_GATHERER_WORKFLOW = 'sample_gather'
TAGASAURIS_VOTING_WORKFLOW = 'voting'

# TODO: XXX: This is ugly... any ideas how to change this?
# NOTE: Please when editing workflows in tagasauris admin update this settings.
TAGASAURIS_NOTIFY = {
    TAGASAURIS_VOTING_WORKFLOW: 'NotifyTask_1',
    TAGASAURIS_SAMPLE_GATHERER_WORKFLOW: 'NotifyTask_2',
}
TAGASAURIS_SURVEY = {
    TAGASAURIS_VOTING_WORKFLOW: 'Survey_0',
    TAGASAURIS_SAMPLE_GATHERER_WORKFLOW: 'Survey_0',
}
TAGASAURIS_FORM = {
    TAGASAURIS_SAMPLE_GATHERER_WORKFLOW: 'Form_1',
}

TAGASAURIS_CALLBACKS = 'http://urlannotator.10clouds.com'
TAGASAURIS_VOTING_CALLBACK = TAGASAURIS_CALLBACKS +\
    '/api/v1/vote/add/tagasauris/%s/'

# Tagasauris needs sacrifice!
DUMMY_URLANNOTATOR_URL =\
    'http://urlannotator.10clouds.com/statics/img/favicon.png'

# Tagasauris will ask for some infro via xhr ($.post() etc). It is different
# domain so we need to allow it explicit.
XS_SHARING_ALLOWED_ORIGINS = TAGASAURIS_HOST
XS_SHARING_ALLOWED_METHODS = ['POST', 'GET']
