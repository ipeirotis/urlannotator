from celery import task, registry, Task

from urlannotator.statistics.job_monitor import JobMonitor, WorkerMonitor
from urlannotator.main.models import (ProgressStatistics, SpentStatistics,
    URLStatistics, LinksStatistics)


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


@task(ignore_result=True)
class URLMonitor(JobMonitor, Task):
    def __init__(self, *args, **kwargs):
        self.model_cls = URLStatistics
        # Warning: Don't use super(self.__class__, ~~ deeper in inheritance -
        # it will cause infinite loop! It's used here because @task decorator
        # manipulates the class itself.
        super(self.__class__, self).__init__(
            cls=URLStatistics,
            *args, **kwargs
        )

    def get_value(self, job):
        return job.get_urls_collected()

url_monitor = registry.tasks[URLMonitor.name]


@task(ignore_result=True)
class LinksMonitor(WorkerMonitor, Task):
    def __init__(self, *args, **kwargs):
        self.model_cls = LinksStatistics
        # Warning: Don't use super(self.__class__, ~~ deeper in inheritance -
        # it will cause infinite loop! It's used here because @task decorator
        # manipulates the class itself.
        super(self.__class__, self).__init__(
            cls=LinksStatistics,
            *args, **kwargs
        )

    def get_value(self, worker):
        return worker.get_links_collected()

links_monitor = registry.tasks[LinksMonitor.name]
