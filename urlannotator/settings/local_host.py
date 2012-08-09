from development import *

JOB_DEFAULT_CLASSIFIER = 'Classifier247'
TWENTYFOUR_DEFAULT_CLASSIFIER = 'SimpleClassifier'


CELERY_RESULT_BACKEND = 'amqp://'
BROKER_URL = 'amqp://'

SITE_URL = '127.0.0.1:8000'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
