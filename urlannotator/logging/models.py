import json

from django.db import models
from tenclouds.django.jsonfield.fields import JSONField

from urlannotator.main.models import Job

# Log types breakdown:
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
        return self.get_action_type_display()

# Log entry stringify functions.


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


class LogEntry(models.Model):
    """
        Contains all logs from the system to be viewed by admins and to
        notify users.
    """
    LOG_TYPES = (
        (LOG_TYPE_JOB_INIT_START, 'Job initialization started.'),
        (LOG_TYPE_JOB_INIT_DONE, 'Job initialization has been completed'),
        (LOG_TYPE_NEW_SAMPLE_START, 'New sample creation has been initiated'),
        (LOG_TYPE_NEW_GOLD_SAMPLE, 'New gold sample has been created'),
        (LOG_TYPE_NEW_SAMPLE_DONE, 'New sample creation has been finished'),
        (LOG_TYPE_CLASS_TRAIN_START, 'Classifier training has been started'),
        (LOG_TYPE_CLASS_TRAIN_DONE, 'Classifier training has been finished'),
        (LOG_TYPE_SAMPLE_CLASSIFIED, 'A new sample has been classified'),
    )

    job = models.ForeignKey(Job)
    date = models.DateTimeField(auto_now_add=True)
    log_type = models.IntegerField(choices=LOG_TYPES)
    log_val = JSONField(default='{}')
    read = models.BooleanField(default=False)

    objects = LogManager()

    def __unicode__(self):
        """
            Parses a log entry into a human-readable form. Used directly in
            alert display for end-users.
        """
        return self.get_log_type_display()
