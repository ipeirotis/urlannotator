import datetime

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
        """
            Scans all active jobs for the ones that require stats
            recomputation. Does it in an infinite loop, after
            settings.JOB_MONITOR_INTERVAL seconds from previous loop.
        """
        jobs = Job.objects.get_active()
        to_handle = []
        for job in jobs:
            latest = self.model_cls.objects.latest_for_job(job)
            if not latest:
                continue
            handle_time = latest.date + self.interval
            if handle_time <= now():
                to_handle.append((job, latest))

        if to_handle:
            self.handle(to_handle)
