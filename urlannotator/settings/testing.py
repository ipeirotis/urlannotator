from development import *

JOB_DEFAULT_CLASSIFIER = 'Classifier247'
TWENTYFOUR_DEFAULT_CLASSIFIER = 'SimpleClassifier'

CELERY_RESULT_BACKEND = 'amqp://'
BROKER_URL = 'amqp://'

# Tools won't access internet resources if this is set to True
TOOLS_TESTING = True
