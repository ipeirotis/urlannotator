from celery import task, registry, Task

from urlannotator.main.models import SpentStatistics
from urlannotator.statistics.job_monitor import JobMonitor


@task(ignore_result=True)
class SpentMonitor(JobMonitor, Task):
    def __init__(self, *args, **kwargs):
        self.model_cls = SpentStatistics
        # Warning: Don't use super(self.__class__, ~~ deeper in inheritance -
        # it will cause infinite loop! It's used here because @task decorator
        # manipulates the class itself.
        super(self.__class__, self).__init__(
            cls=SpentStatistics,
            *args, **kwargs
        )

    def get_value(self, job):
        return job.budget

spent_monitor = registry.tasks[SpentMonitor.name]
