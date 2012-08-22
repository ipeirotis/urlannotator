import json

from django.db import models
from tenclouds.django.jsonfield.fields import JSONField

from urlannotator.main.models import Job

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
        'Console_out': 'Job\'s %(job_id)d initialization has been started.',
    },
    LOG_TYPE_JOB_INIT_DONE: {
        'Console_out': 'Job\'s %(job_id)d initialization has been completed.',
    },
    LOG_TYPE_NEW_SAMPLE_START: {
        'Console_out': 'New sample is being created (%(log_val)s).',
    },
    LOG_TYPE_NEW_GOLD_SAMPLE: {
        'Console_out': 'New gold sample is being created (%(log_val)s).',
    },
    LOG_TYPE_NEW_SAMPLE_DONE: {
        'Console_out': 'New sample has been created (%(log_val)s).',
        'Single_text': 'New sample (%(sample_url)s) has been created.',
        'Plural_text': 'New samples have been created.',
        'Show_users': True,
        'Box_entry': {
            'Title': 'New Sample',
            'Text': '<a href="%(sample_url)s">%(sample_url)s</a>',
        },
    },
    LOG_TYPE_CLASS_TRAIN_START: {
        'Console_out': 'Classifier is being trained (%(log_val)s).',
    },
    LOG_TYPE_CLASS_TRAIN_DONE: {
        'Console_out': 'Classifier training has finished (%(log_val)s).',
    },
    LOG_TYPE_SAMPLE_CLASSIFIED: {
        'Console_out': 'Sample has been classified (%(log_val)s).',
    },
}


def log_config_get(log_type, attrs):
    """
        Gets given config attr for log_type. If not present, gets the attrs for
        default config. If missing, returns None.
        Attrs can be a list of attributes for nested lookup.
    """
    default = log_config[LOG_TYPE_DEFAULT]
    value = log_config[log_type]
    for attr in attrs:
        value = value.get(attr, None)
        default = default[attr]
        if not value:
            value = default

    return value

# Long actions formats
long_single = {
    LONG_ACTION_TRAINING:
    '<a href="%(job_url)s">Your job\'s</a> classifier is under training.',
}

long_plural = {
    LONG_ACTION_TRAINING: 'Classifiers\' are being trained.',
}


class LongActionManager(models.Manager):
    """
        Manages long actions.
    """
    def running_for_user(self, user, *args, **kwargs):
        account = user.get_profile()
        jobs = Job.objects.filter(account=account)
        actions = super(LongActionManager, self).get_query_set().filter(
            job__in=jobs,
        )
        return actions

    def start_action(self, action_type, job, *args, **kwargs):
        self.create(
            job=job,
            action_type=action_type,
        )

    def finish_action(self, action_type, job, *args, **kwargs):
        self.get_query_set().filter(
            job=job,
            action_type=action_type,
        ).delete()


class LongActionEntry(models.Model):
    """
        Contains entries from current long-term running actions for a given job
    """
    LONG_ACTIONS = (
        (LONG_ACTION_TRAINING, "Classifier is being trained"),
    )

    job = models.ForeignKey(Job)
    action_type = models.IntegerField(choices=LONG_ACTIONS)

    objects = LongActionManager()

    def __unicode__(self):
        """
            Single action's string with it's parameters.
        """
        format_dict = {
            'job_url': self.job.get_absolute_url(),
        }
        format_string = long_single[self.action_type]
        return format_string % format_dict

    def get_plural_text(self):
        return long_plural[self.action_type]


class LogManager(models.Manager):
    """
        Manages creation of logs.
    """
    def log(self, log_type, job, params={}, *args, **kwargs):
        """
            Creates new log entry.
        """
        self.create(
            job=job,
            log_type=log_type,
            log_val=json.dumps(params)
        )


def generate_log_types():
    """
        Generates a list of tuples (log_id, log_text) and returns it.
    """
    log_list = [(log_id, log_config_get(log_id, ['Single_text']))
        for log_id, log in log_config.items()]
    return list(log_list)


class LogEntry(models.Model):
    """
        Contains all logs from the system to be viewed by admins and to
        notify users.
    """
    LOG_TYPES = generate_log_types()

    job = models.ForeignKey(Job)
    date = models.DateTimeField(auto_now_add=True)
    log_type = models.IntegerField(choices=LOG_TYPES)
    log_val = JSONField(default='{}')
    read = models.BooleanField(default=False)

    objects = LogManager()

    def __unicode__(self):
        return self.get_console_text()

    def get_console_text(self):
        """
            Return a console output of the log entry.
        """
        return self.format_config_string(['Console_out'])

    def format_string(self, string):
        """
            Formats given string using local dictionary.
        """
        format_dict = {
            'job_url': self.job.get_absolute_url(),
            'job_id': self.job.id,
            'log_type': self.log_type,
            'log_val': self.log_val,
        }
        format_dict = dict(format_dict.items() + self.log_val.items())
        return string % format_dict

    def format_config_string(self, attrs):
        """
            Formats and returns a config string.
            Attrs is a list of attributes on the path to the element in config
            tree.
        """
        val = log_config_get(self.log_type, attrs)
        return self.format_string(val)

    def get_single_text(self):
        """
            Parses a log entry into a human-readable form. Used directly in
            alert display for end-users.
        """
        return self.format_config_string(['Single_text'])

    def get_plural_text(self):
        """
            Returns a plural text for log entry. Used in aggregating.
        """
        return self.format_config_string(['Plural_text'])

    def get_box(self):
        """
            Returns a dictionary of values used in filling the updates box
            entry.
        """
        val = {
            'Title': self.format_config_string(['Box_entry', 'Title']),
            'Text': self.format_config_string(['Box_entry', 'Text']),
            'Image_url': self.format_config_string(['Box_entry', 'Image_url']),
            'By': self.format_config_string(['Box_entry', 'By']),
            'By_id': log_config_get(self.log_type, ['Box_entry', 'By_id']),
        }
        return val
