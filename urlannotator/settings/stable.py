from defaults import *
from imagescale2 import *
from imagescale2 import DEF_PORT as IMAGESCALE_DEF_PORT

DEBUG = False
TEMPLATE_DEBUG = DEBUG
JS_DEBUG = DEBUG
PIPELINE = True

SOCIAL_AUTH_RAISE_EXCEPTIONS = False

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(ROOT_DIR, '..', 'database.sqlite3.db'),
    }
}

KEY_PREFIX = 'stable_urlannotator'

MIDDLEWARE_CLASSES = tuple(list(MIDDLEWARE_CLASSES) + [
        'pipeline.middleware.MinifyHTMLMiddleware',
])

# Production Mail settings
SERVER_EMAIL = DEFAULT_FROM_EMAIL = 'noreply@urlannotator'
EMAIL_HOST = 'localhost'
EMAIL_PORT = 25
EMAIL_USE_TLS = False
EMAIL_HOST_USER = None
EMAIL_HOST_PASSWORD = None

# django sentry
SENTRY_DSN = 'http://d0cf3412cdd74976abcb9b4ebcce906c:48f0cece0ff14bf490bcfe9249f4e231@sentry.10clouds.com/9'
INSTALLED_APPS = INSTALLED_APPS + (
    'raven.contrib.django',
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(ROOT_DIR, '..', 'database.sqlite3.db'),
    }
}

CACHES['memcache']['KEY_PREFIX'] = KEY_PREFIX

JOB_DEFAULT_CLASSIFIER = 'Classifier247'
TWENTYFOUR_DEFAULT_CLASSIFIER = 'GooglePredictionClassifier'

SITE_URL = 'buildaclassifier.com'
IMAGESCALE_URL = '127.0.0.1:%d' % IMAGESCALE_DEF_PORT

EMAIL_BACKEND = 'urlannotator.main.backends.email.EmailBackend'

# Broker for celery
BROKER_URL = 'amqp://guest@localhost:5674/'


local_settings = os.path.join(os.path.dirname(__file__), 'local.py')
if os.path.isfile(local_settings):
    from local import *

# Tagasauris settings
TAGASAURIS_LOGIN = 'urlannotator'
TAGASAURIS_PASS = 'GomObUdcor1'
TAGASAURIS_HOST = 'http://stable.tagasauris.com'
TAGASAURIS_USE_SANDBOX = False

TAGASAURIS_HIT_TYPE = TAGASAURIS_MTURK
TAGASAURIS_HIT_URL = TAGASAURIS_HIT_MTURK_URL

# TODO: This is ugly... any ideas how to change this?
TAGASAURIS_NOTIFY = {
    TAGASAURIS_VOTING_WORKFLOW: 'NotifyTask_1',
    TAGASAURIS_SAMPLE_GATHERER_WORKFLOW: 'NotifyTask_2',
}

TAGASAURIS_CALLBACKS = 'http://' + SITE_URL
TAGASAURIS_VOTING_CALLBACK = TAGASAURIS_CALLBACKS +\
    '/api/v1/vote/add/tagasauris/%s/'
TAGASAURIS_BTM_VOTING_CALLBACK = TAGASAURIS_CALLBACKS +\
    '/api/v1/vote/btm/tagasauris/%s/'

TAGASAURIS_HIT_SOCIAL_URL = TAGASAURIS_HOST + '/actions/start_annotation/?hid=%s'

# Tagasauris needs sacrifice!
DUMMY_URLANNOTATOR_URL =\
    'http://' + SITE_URL + '/statics/img/favicon.png'

XS_SHARING_ALLOWED_ORIGINS = TAGASAURIS_HOST

PIPELINE = not DEBUG
if PIPELINE:
    STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'
