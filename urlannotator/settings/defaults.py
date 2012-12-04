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

ADMINS = (
  ('mickek', 'michal.klujszo@10clouds.com'),
  ('maciej.gol', 'maciej.gol@10clouds.com'),
  ('przemyslaw.spodymek', 'przemyslaw.spodymek@10clouds.com')
)
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
VOTES_STORAGE = 'TroiaVotesStorage'
QUALITY_ALGORITHM = 'DawidSkeneAlgorithm'

SITE_URL = 'devel.urlannotator.10clouds.com'

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
    },
    'memcache': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'KEY_PREFIX': 'devel_urlannotator',
        'TIMEOUT': 30,
    },

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
    'tenclouds.crud',

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
    'urlannotator.payments',
)

INSTALLED_APPS = BASE_APPS + PROJECT_APPS

# use django_extensions if available
try:
    # very useful utilities, take a look at
    # http://packages.python.org/django-extensions/
    __import__("django_extensions")

    INSTALLED_APPS = tuple(list(INSTALLED_APPS) + [
        'django_extensions',
    ])
except ImportError:
    pass

SOCIAL_AUTH_PROTECTED_USER_FIELDS = ['email', 'username']
SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/'
SOCIAL_AUTH_NEW_USER_REDIRECT_URL = '/settings/'
SOCIAL_AUTH_NEW_ASSOCIATION_REDIRECT_URL = '/settings/'
SOCIAL_AUTH_DISCONNECT_REDIRECT_URL = '/settings/'
LOGIN_REDIRECT_URL = ''
LOGIN_URL = '/login/'
LOGIN_ERROR_URL = '/login/'
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
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(message)s'
        },
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'urlannotator': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        }
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

CELERY_CREATE_MISSING_QUEUES = True
CELERY_ROUTES = {}

# Celery queues usage and designated tasks breakdown:
# Default ('celery') - all short-timed events and flow control events.
#                      All tasks are routed here by default.
CELERY_DEFAULT_QUEUE = 'celery'

# Real-time ('realtime-tasks') - short (!) tasks that should be handled ASAP.
CELERY_REALTIME_QUEUE = 'realtime-tasks'

# Long-scarce ('long-scarce-tasks') - tasks that take long to complete, but are
#             not that frequently sent. Usually sent by CeleryBeat.
#
CELERY_LONGSCARCE_QUEUE = 'long-scarce-tasks'

# Long-common ('long-common-tasks') - tasks that can take really long to
#                                     complete and are pretty common
#                                     in the system.
# These have to be here because they are called without our event bus.
CELERY_LONGCOMMON_QUEUE = 'long-common-tasks'
long_common = (
    ('urlannotator.main.tasks.web_content_extraction'),
    ('urlannotator.main.tasks.web_screenshot_extraction'),
)

# Celery worker distribution (num of workers, queues):
# 1 worker - default, realtime-tasks
# 1 worker - realtime-tasks
# 2 workers - long-scarce-tasks, realtime-tasks, default
# 4 workers - long-common-tasks, realtime-tasks, default


def register_to_queues(tasks, queue_name):
    for task in tasks:
        CELERY_ROUTES[task] = {
            'queue': queue_name,
        }

register_to_queues(long_common, 'long-common-tasks')

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
        'options': {
            'queue': CELERY_LONGSCARCE_QUEUE,
        },
    },
    'url_monitor': {
        'task': 'urlannotator.statistics.monitor_tasks.URLMonitor',
        'schedule': JOB_MONITOR_INTERVAL,
        'kwargs': {'interval': JOB_MONITOR_ENTRY_INTERVAL},
        'options': {
            'queue': CELERY_LONGSCARCE_QUEUE,
        },
    },
    'progress_monitor': {
        'task': 'urlannotator.statistics.monitor_tasks.ProgressMonitor',
        'schedule': JOB_MONITOR_INTERVAL,
        'kwargs': {'interval': JOB_MONITOR_ENTRY_INTERVAL},
        'options': {
            'queue': CELERY_LONGSCARCE_QUEUE,
        },
    },
    'votes_monitor': {
        'task': 'urlannotator.statistics.monitor_tasks.VotesMonitor',
        'schedule': JOB_MONITOR_INTERVAL,
        'kwargs': {'interval': JOB_MONITOR_ENTRY_INTERVAL},
        'options': {
            'queue': CELERY_LONGSCARCE_QUEUE,
        },
    },
    'links_monitor': {
        'task': 'urlannotator.statistics.monitor_tasks.LinksMonitor',
        'schedule': WORKER_MONITOR_INTERVAL,
        'kwargs': {'interval': datetime.timedelta(days=1)},
        'options': {
            'queue': CELERY_LONGSCARCE_QUEUE,
        },
    },
    'send_validated_samples': {
        'task': 'urlannotator.classification.event_handlers.SampleVotingManager',
        'schedule': datetime.timedelta(seconds=3 * 60),
        'args': [],
        'options': {
            'queue': CELERY_LONGSCARCE_QUEUE,
        },
    },
    'process_votes': {
        'task': 'urlannotator.classification.event_handlers.ProcessVotesManager',
        'schedule': datetime.timedelta(seconds=3 * 60),
        'args': [],
        'options': {
            'queue': CELERY_LONGSCARCE_QUEUE,
        },
    },
    'samplegather_hit': {
        'task': 'urlannotator.classification.event_handlers.SampleGatheringHITMonitor',
        'schedule': datetime.timedelta(seconds=3 * 60),
        'args': [],
        'options': {
            'queue': CELERY_LONGSCARCE_QUEUE,
        },
    },
    'voting_hit': {
        'task': 'urlannotator.classification.event_handlers.VotingHITMonitor',
        'schedule': datetime.timedelta(seconds=3 * 60),
        'args': [],
        'options': {
            'queue': CELERY_LONGSCARCE_QUEUE,
        },
    },
    'btm_gather_hit': {
        'task': 'urlannotator.classification.event_handlers.BTMGatheringHITMonitor',
        'schedule': datetime.timedelta(seconds=3 * 60),
        'args': [],
        'options': {
            'queue': CELERY_LONGSCARCE_QUEUE,
        },
    },
    'btm_voting_hit': {
        'task': 'urlannotator.classification.event_handlers.BTMVotingHITMonitor',
        'schedule': datetime.timedelta(seconds=3 * 60),
        'args': [],
        'options': {
            'queue': CELERY_LONGSCARCE_QUEUE,
        },
    },
    'odesk_monitor': {
        'task': 'urlannotator.crowdsourcing.event_handlers.OdeskJobMonitor',
        'schedule': datetime.timedelta(seconds=3 * 60),
        'args': [],
        'options': {
            'queue': CELERY_LONGSCARCE_QUEUE,
        },
    },
}

# Test runner
# CELERY_ALWAYS_EAGER = True
TEST_RUNNER = 'djcelery.contrib.test_runner.CeleryTestSuiteRunner'

# Tagasauris integretion settings
# NOTE 1: Tagasauris account must have disabled "billings" option.
# NOTE 2: Tagasauris Workflows must have set "external" flag.

TAGASAURIS_HOST = 'http://devel.tagasauris.com'  # Mind updating XS_SHARING_*
TAGASAURIS_USE_SANDBOX = True

TAGASAURIS_HIT_SANDBOX_URL = "https://workersandbox.mturk.com/mturk/preview?groupId=%s"
TAGASAURIS_HIT_MTURK_URL = "https://mturk.com/mturk/preview?groupId=%s"

TAGASAURIS_HIT_URL = TAGASAURIS_HIT_SANDBOX_URL

TAGASAURIS_MTURK = 'mturk'
TAGASAURIS_SOCIAL = 'social'

ODESK_HIT_TYPE = TAGASAURIS_SOCIAL
OWN_WORKFORCE_HIT_TYPE = TAGASAURIS_MTURK

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

TAGASAURIS_GATHER_PRICE = "0.10"
TAGASAURIS_VOTE_PRICE = "0.06"
TAGASAURIS_BTM_PRICE = "0.04"
TAGASAURIS_VOTE_MEDIA_PER_HIT = 10
TAGASAURIS_VOTE_WORKERS_PER_HIT = 3
TAGASAURIS_GATHER_INSTRUCTION_URL = \
    "https://s3.amazonaws.com/instructions.buildaclassifier.com/gatherer.task.html"
TAGASAURIS_VOTING_INSTRUCTION_URL = \
    "https://s3.amazonaws.com/instructions.buildaclassifier.com/voting.task.html"

# Tagasauris will ask for some info via xhr ($.post() etc). It is different
# domain so we need to allow it explicit.
XS_ON_NGINX = True
XS_SHARING_ALLOWED_ORIGINS = TAGASAURIS_HOST
XS_SHARING_ALLOWED_METHODS = ['POST', 'GET']
