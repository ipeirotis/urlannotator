from celery import task, registry, Task

from urlannotator.statistics.job_monitor import JobMonitor
from urlannotator.main.models import ProgressStatistics


@task(ignore_result=True)
class ProgressMonitor(JobMonitor, Task):
    def __init__(self, *args, **kwargs):
        self.model_cls = ProgressStatistics
        # Warning: Don't use super(self.__class__, ~~ deeper in inheritance -
        # it will cause infinite loop! It's used here because @task decorator
        # manipulates the class itself.
        super(self.__class__, self).__init__(
            cls=ProgressStatistics,
            *args, **kwargs
        )

    def get_value(self, job):
        return job.get_progress()

progress_monitor = registry.tasks[ProgressMonitor.name]
