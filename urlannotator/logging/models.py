import json

from django.db import models
from tenclouds.django.jsonfield.fields import JSONField

from urlannotator.main.models import Job
from urlannotator.logging.settings import log_config_get, generate_log_types
from urlannotator.logging.settings import (LONG_ACTION_TRAINING, long_single,
    long_plural)


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
        self.get_single_text()

    def get_single_text(self):
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
        return self.create(
            job=job,
            log_type=log_type,
            log_val=json.dumps(params)
        )

    def unread_for_user(self, user):
        """
            Returns all unread logs for user.
        """
        jobs = user.get_profile().job_set.all()
        entries = self.filter(job__in=jobs, read=False)
        res = [entry for entry in entries if entry.is_visible_to_users()]
        entries.update(read=True)
        return res

    def recent_for_job(self, job=None, num=4, user_visible=True):
        """
            Returns `num` recent logs for given job.

            :param job: job logs should be returned for. If `None`,
                        display all.
            :param num: up to how many results should be returned. 0 means all.
            :param user_visible: whether return only those visible for users
        """
        if job:
            logs = self.filter(job=job).order_by('-id')
        else:
            logs = self.all().order_by('-id')

        recent_list = [log for log in logs
            if (not user_visible or log.is_visible_to_users())]

        if num:
            return recent_list[:num]
        else:
            return recent_list


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
            'Job_id': self.job_id,
        }
        return val

    def is_visible_to_users(self):
        """
            Returns whether given entry is visible to users (via alerts or
            updates box)
        """
        return log_config_get(self.log_type, ['Show_users'])
