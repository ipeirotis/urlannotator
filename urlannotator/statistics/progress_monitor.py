import datetime

from celery import task, registry, Task

from urlannotator.statistics.job_monitor import extract
from urlannotator.main.models import ProgressStatistics


@task(ignore_result=True)
class ProgressMonitor(Task):
    def __init__(self, interval=datetime.timedelta(hours=1)):
        self.interval = interval
        self.model_cls = ProgressStatistics

    def get_value(self, job):
        div = job.no_of_urls or 1
        return (job.no_of_urls - job.remaining_urls) / div * 100

    def run(self):
        extract(self)

progress_monitor = registry.tasks[ProgressMonitor.name]
