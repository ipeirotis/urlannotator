from development import *

JOB_DEFAULT_CLASSIFIER = 'Classifier247'
TWENTYFOUR_DEFAULT_CLASSIFIER = 'SimpleClassifier'

CELERY_RESULT_BACKEND = 'amqp://'
BROKER_URL = 'amqp://'

# Several tools won't access resources if this is set to True.
TOOLS_TESTING = True
DEBUG = False
