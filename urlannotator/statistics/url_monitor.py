from celery import task, registry
from django.conf import settings

from urlannotator.statistics.job_monitor import JobMonitor
from urlannotator.main.models import URLStatistics


@task()
class URLMonitor(JobMonitor):
    def __init__(self, **kwargs):
        super(URLMonitor, self).__init__(
            cls=URLStatistics,
            interval=settings.URL_MONITOR_STAT_INTERVAL,
            **kwargs
        )

    def get_value(self, job):
        return job.no_of_urls - job.remaining_urls

url_monitor = registry.tasks[URLMonitor.name]
