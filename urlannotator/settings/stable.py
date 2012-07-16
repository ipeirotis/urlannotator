from defaults import *

DEBUG = False
TEMPLATE_DEBUG = DEBUG
JS_DEBUG = DEBUG
PIPELINE = True

DATABASES.update({
    'default': {
        'ENGINE': 'django.db.backends.',
        'NAME': 'urlannotator_stable',
        'PORT': '',
        'USER': 'urlannotator_stable',
        'PASSWORD': '10clouds',
        'HOST': '',
        'OPTIONS': {}
    },
})

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
SENTRY_DSN = None
INSTALLED_APPS = INSTALLED_APPS + (
    'raven.contrib.django',
)

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
