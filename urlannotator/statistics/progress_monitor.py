from celery import task, registry
from django.conf import settings

from urlannotator.statistics.job_monitor import JobMonitor
from urlannotator.main.models import ProgressStatistics


@task()
class ProgressMonitor(JobMonitor):
    def __init__(self, **kwargs):
        super(ProgressMonitor, self).__init__(
            cls=ProgressStatistics,
            interval=settings.PROGRESS_MONITOR_STAT_INTERVAL,
            **kwargs
        )

    def get_value(self, job):
        div = job.no_of_urls or 1
        return (job.no_of_urls - job.remaining_urls) / div * 100

progress_monitor = registry.tasks[ProgressMonitor.name]
