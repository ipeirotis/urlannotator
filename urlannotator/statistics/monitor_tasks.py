from celery import task, registry, Task

from urlannotator.statistics.monitors import (JobMonitor, WorkerMonitor,
    WorkerJobMonitor)
from urlannotator.main.models import (ProgressStatistics, SpentStatistics,
    URLStatistics, LinksStatistics, VotesStatistics, WorkerJobURLStatistics)


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
        return job.get_progress(cache=False)

    def after_handle(self, obj_set):
        for job in obj_set:
            job.get_progress_stats(cache=False)

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

    def after_handle(self, obj_set):
        for job in obj_set:
            job.get_spent_stats(cache=False)


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

    def after_handle(self, obj_set):
        for job in obj_set:
            job.get_urls_stats(cache=False)


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


@task(ignore_result=True)
class WorkerJobURLMonitor(WorkerJobMonitor, Task):
    def __init__(self, *args, **kwargs):
        self.model_cls = WorkerJobURLStatistics
        # Warning: Don't use super(self.__class__, ~~ deeper in inheritance -
        # it will cause infinite loop! It's used here because @task decorator
        # manipulates the class itself.
        super(self.__class__, self).__init__(
            cls=WorkerJobURLStatistics,
            *args, **kwargs
        )

    def get_value(self, worker_assoc):
        return worker_assoc.get_urls_collected(cache=False)

    def after_handle(self, obj_list):
        for assoc in obj_list:
            assoc.get_url_collected_stats(cache=False)

worker_job_url_monitor = registry.tasks[WorkerJobURLMonitor.name]


@task(ignore_result=True)
class VotesMonitor(JobMonitor, Task):
    def __init__(self, *args, **kwargs):
        self.model_cls = VotesStatistics
        # Warning: Don't use super(self.__class__, ~~ deeper in inheritance -
        # it will cause infinite loop! It's used here because @task decorator
        # manipulates the class itself.
        super(self.__class__, self).__init__(
            cls=VotesStatistics,
            *args, **kwargs
        )

    def get_value(self, job):
        return job.get_votes_gathered(cache=False)

    def after_handle(self, obj_set):
        for job in obj_set:
            job.get_votes_stats(cache=False)


votes_monitor = registry.tasks[VotesMonitor.name]
