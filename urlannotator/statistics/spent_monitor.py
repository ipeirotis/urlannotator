from celery import task, registry
from django.conf import settings

from urlannotator.statistics.job_monitor import JobMonitor
from urlannotator.main.models import SpentStatistics


@task(ignore_result=True)
class SpentMonitor(JobMonitor):
    def __init__(self, **kwargs):
        super(SpentMonitor, self).__init__(
            cls=SpentStatistics,
            interval=settings.SPENT_MONITOR_STAT_INTERVAL,
            **kwargs
        )

    def get_value(self, job):
        return job.budget

spent_monitor = registry.tasks[SpentMonitor.name]
