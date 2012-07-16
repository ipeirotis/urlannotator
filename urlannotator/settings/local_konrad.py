
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,

    'formatters': {
        'verbose': {
            'format': '%(name)s %(levelname)s %(asctime)s %(pathname)s:'
            '%(funcName)s:%(lineno)d\n%(message)s'
            '\n==============================='
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },

    'handlers': {
        'console': {
            'level': 'WARNING',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        }
    },

    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'south': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False,
        },
    },
    "root": {
        "handlers": ["console"],
        'level': 'DEBUG'
    }
}


CELERY_RESULT_BACKEND = 'amqp://'
BROKER_URL = 'amqp://'
