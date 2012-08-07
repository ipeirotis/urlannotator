import datetime

from celery import task, registry, Task

from urlannotator.main.models import SpentStatistics
from urlannotator.statistics.job_monitor import extract


@task(ignore_result=True)
class SpentMonitor(Task):
    # FIXME: Possible inheritance to JobMonitor without breaking Task?
    def __init__(self, interval=datetime.timedelta(seconds=1)):
        self.interval = interval
        self.model_cls = SpentStatistics

    def get_value(self, job):
        return job.budget

    def run(self):
        extract(self)


spent_monitor = registry.tasks[SpentMonitor.name]
