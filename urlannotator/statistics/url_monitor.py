import datetime

from celery import task, registry, Task

from urlannotator.statistics.job_monitor import extract
from urlannotator.main.models import URLStatistics


@task(ignore_result=True)
class URLMonitor(Task):
    def __init__(self, interval=datetime.timedelta(seconds=1)):
        self.interval = interval
        self.model_cls = URLStatistics

    def get_value(self, job):
        return job.no_of_urls - job.remaining_urls

    def run(self):
        extract(self)

url_monitor = registry.tasks[URLMonitor.name]
