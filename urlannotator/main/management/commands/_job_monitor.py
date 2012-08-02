import datetime
import time

from django.conf import settings
from django.utils.timezone import now

from urlannotator.main.models import Job


class JobMonitor(object):
    """
        Every JOB_MONITOR_INTERVAL queries for jobs requiring statistics
        recomputation and does it.
        Interval argument has to be an instance of datetime.timedelta.
        Requires model class's manager to implement 'latest_for_job(job)',
        where job is an instance of Job model.
        Inheriting classes MUST define get_value(job) method.
    """
    def __init__(self, cls, interval=datetime.timedelta(hours=1)):
        self.time_interval = settings.JOB_MONITOR_INTERVAL
        self.interval = interval
        self.model_cls = cls

    def handle(self, job_set):
        """
            Handles performing periodic tasks on computed job set. Job set is
            a list of 2-tuples (job, old statistic entry).
        """
        for job in job_set:
            old_value = job[1].value
            new_value = self.get_value(job[0])
            delta = new_value - old_value
            print ('Saving new stat', self.model_cls.__name__, 'of', delta,
                '(', new_value, ')', 'for job', job[0].id)
            self.model_cls.objects.create(
                job=job[0],
                value=new_value,
                delta=delta
            )

    def get_value(self, job):
        """
            Gets job-specific statistic.
        """
        return 0

    def run(self):
        while True:
            jobs = Job.objects.get_active()
            to_handle = []
            print 'active jobs', jobs
            for job in jobs:
                latest = self.model_cls.objects.latest_for_job(job)
                if not latest:
                    continue
                handle_time = latest.date + self.interval
                print 'handle time for job', job.id, 'is', handle_time
                print 'now', now()
                if handle_time <= now():
                    to_handle.append((job, latest))

            if to_handle:
                self.handle(to_handle)
            time.sleep(self.time_interval)
