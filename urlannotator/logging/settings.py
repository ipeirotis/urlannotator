# Log types breakdown:
LOG_TYPE_DEFAULT = -1  # Default log type settings
LOG_TYPE_JOB_INIT_START = 0  # Job initialization has been started
LOG_TYPE_JOB_INIT_DONE = 1  # Job initialization has been completed
LOG_TYPE_NEW_SAMPLE_START = 2  # New sample creation has been initiated
LOG_TYPE_NEW_GOLD_SAMPLE = 3  # New gold sample has been created
LOG_TYPE_NEW_SAMPLE_DONE = 4  # New sample creation has been finished
LOG_TYPE_CLASS_TRAIN_START = 5  # Classifier training has been started
LOG_TYPE_CLASS_TRAIN_DONE = 6  # Classifier training has been finished
LOG_TYPE_SAMPLE_CLASSIFIED = 7  # A new sample has been classified
LOG_TYPE_SAMPLE_SCREENSHOT_DONE = 8  # Sample's screenshot has been taken
LOG_TYPE_SAMPLE_TEXT_DONE = 9  # Sample's text has been extracted
LOG_TYPE_SAMPLE_SCREENSHOT_FAIL = 10  # Error while taking screenshot
LOG_TYPE_SAMPLE_TEXT_FAIL = 11  # Error while getting content
LOG_TYPE_CLASSIFIER_TRAINING_ERROR = 12  # Error while training. Can retry.
LOG_TYPE_CLASSIFIER_FATAL_TRAINING_ERROR = 13  # Fatal error while training. Aborted.

# Long action type breakdown:
LONG_ACTION_TRAINING = 1  # Classifier training

# Log configurations
# Configuration template:
# 'Single_text' - event description in singular form.
# 'Plural_text' - event description in plural form.
# 'Box_entry' - dictionary of settings used in formatting updates box entries.
#   'Title' - entry title
#   'Text' - entry text.
#   'Image_url' - url of alert's image.
#   'By_id' - id of worker that triggered the log.
#   'By' - name of the worker that triggered the log.
# 'Show_users' - whether log can be shown to users in alerts/updates box.
# 'Console_out' - event description when printing out to the console. Also
#                 used in entry.__unicode__() method
#
# Following variables are available in strings:
#   'job_url', 'job_id', any variable from entry.log_val dictionary,
#   'log_val', 'log_type', 'worker_id' (defaults to 0), 'worker_name' (defaults
#   to an empty string)
# If a config entry is missing some values, default ones are used.

log_config = {
    LOG_TYPE_DEFAULT: {
        'Single_text': 'Event',
        'Plural_text': 'Events',
        'Box_entry': {
            'Title': 'Event',
            'Text': 'Event text.',
            'Image_url': '',
            'By_id': 0,
            'By': '',
        },
        'Show_users': False,
        'Console_out': 'Event %(log_type)s (%(log_val)s).',
    },
    LOG_TYPE_JOB_INIT_START: {
        'Console_out': 'Job %(job_id)d\'s initialization has been started.',
    },
    LOG_TYPE_JOB_INIT_DONE: {
        'Console_out': 'Job %(job_id)d\'s initialization has been completed.',
    },
    LOG_TYPE_NEW_SAMPLE_START: {
        'Console_out': 'New sample is being created (%(log_val)s).',
    },
    LOG_TYPE_NEW_GOLD_SAMPLE: {
        'Show_users': True,
        'Single_text': 'New gold sample (%(gold_url)s) has been created.',
        'Plural_text': 'New gold samples have been created.',
        'Box_entry': {
            'Title': 'New Gold Sample',
            'Text': '<a href="%(gold_url)s">%(gold_url)s</a>',
            'Image_url': '%(sample_image)s',
        },
        'Console_out': 'New gold sample has been created (%(log_val)s).',
    },
    LOG_TYPE_NEW_SAMPLE_DONE: {
        'Console_out': 'New sample has been created (%(log_val)s).',
        'Single_text': 'New sample (%(sample_url)s) has been created.',
        'Plural_text': 'New samples have been created.',
        'Show_users': True,
        'Box_entry': {
            'Title': 'New Sample',
            'Text': '<a href="%(sample_url)s">%(sample_url)s</a>',
            'Image_url': '%(sample_image)s',
        },
    },
    LOG_TYPE_CLASS_TRAIN_START: {
        'Show_users': True,
        'Single_text': 'Classifier is being trained.',
        'Plural_text': 'Classifiers are being trained.',
        'Show_users': True,
        'Box_entry': {
            'Title': 'Classifier Training',
            'Text': 'Started',
        },
        'Console_out': 'Classifier is being trained (%(log_val)s).',
    },
    LOG_TYPE_CLASS_TRAIN_DONE: {
        'Show_users': True,
        'Single_text': 'Classifier training has been finished.',
        'Plural_text': 'Classifiers\' training has been finished.',
        'Show_users': True,
        'Box_entry': {
            'Title': 'Classifier Training',
            'Text': 'Done',
        },
        'Console_out': 'Classifier training has finished (%(log_val)s).',
    },
    LOG_TYPE_SAMPLE_CLASSIFIED: {
        'Console_out': 'Sample has been classified (%(log_val)s).',
        'Single_text': 'New sample (%(class_url)s) has been classified.',
        'Plural_text': 'New samples have been classified.',
        'Show_users': True,
        'Box_entry': {
            'Title': 'Sample Classified',
            'Text': '<a href="%(class_url)s">%(class_url)s</a>',
            'Image_url': '%(sample_image)s',
        },
    },
    LOG_TYPE_SAMPLE_SCREENSHOT_DONE: {
        'Console_out': 'Sample\'s screenshot has been created (%(log_val)s).',
        'Single_text': 'New sample screenshot (%(sample_url)s).',
        'Plural_text': 'New sample screenshots.',
        'Show_users': True,
        'Box_entry': {
            'Title': 'New Screenshot',
            'Text': '<a href="%(sample_url)s">%(sample_url)s</a>',
        },
    },
    LOG_TYPE_SAMPLE_TEXT_DONE: {
        'Console_out': 'Sample\'s text has been extracted (%(log_val)s).',
        'Single_text': 'New sample content (%(sample_url)s).',
        'Plural_text': 'New sample contents.',
        'Show_users': True,
        'Box_entry': {
            'Title': 'New Content',
            'Text': '<a href="%(sample_url)s">%(sample_url)s</a>',
        },
    },
    LOG_TYPE_SAMPLE_SCREENSHOT_FAIL: {
        'Console_out': 'Error while taking screenshot (%(sample_url)s)'
                       ' - code %(error_code)d.',
        'Single_text': 'Sample screenshot failed (%(sample_url)s).',
        'Plural_text': 'Sample screenshots failed.',
        'Show_users': True,
        'Box_entry': {
            'Title': 'Screenshot failed',
            'Text': '<a href="%(sample_url)s">%(sample_url)s</a>',
        },
    },
    LOG_TYPE_SAMPLE_TEXT_FAIL: {
        'Console_out': 'Error while getting content (%(sample_url)s)'
                       ' - code %(error_code)d.',
        'Single_text': 'Sample content failed (%(sample_url)s).',
        'Plural_text': 'Sample contents failed.',
        'Show_users': True,
        'Box_entry': {
            'Title': 'Content failed',
            'Text': '<a href="%(sample_url)s">%(sample_url)s</a>',
        },
    },
    LOG_TYPE_CLASSIFIER_TRAINING_ERROR: {
        'Console_out': 'Error while training classifier for job (%(job_id)d)'
                       ' - %(error_message)s.',
    },
    LOG_TYPE_CLASSIFIER_FATAL_TRAINING_ERROR: {
        'Console_out': 'Fatal error while training classifier for job '
                       '(%(job_id)d) - %(error_message)s.',
        'Single_text': 'Fatal error while training classifier.',
        'Plural_text': 'Fatal error while training classifiers.',
        'Show_users': True,
        'Box_entry': {
            'Title': 'Fatal error',
            'Text': 'Classifier training failed.',
        },
    },
}


def log_config_get(log_type, attrs):
    """
        Gets given config attr for log_type. If not present, gets the attrs for
        default config. If missing, returns None.
        Attrs can be a list of attributes for nested lookup.
    """
    if not log_type in log_config:
        return None

    default = log_config[LOG_TYPE_DEFAULT]
    value = log_config[log_type]
    for attr in attrs:
        value = value.get(attr, None)
        default = default[attr]
        if not value:
            value = default

    return value


def generate_log_types():
    """
        Generates a list of tuples (log_id, log_text) and returns it.
    """
    log_list = [(log_id, log_config_get(log_id, ['Single_text']))
        for log_id, log in log_config.items()]
    return list(log_list)

# Long actions formats
long_single = {
    LONG_ACTION_TRAINING:
    '<a href="%(job_url)s">Your job\'s</a> classifier is under training.',
}

long_plural = {
    LONG_ACTION_TRAINING: 'Classifiers are being trained.',
}
