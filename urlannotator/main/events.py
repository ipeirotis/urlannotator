from django.conf import settings

from celery import task, Task, registry
from factories import SampleFactory, JobFactory


@task()
class EventRawSampleManager(Task):
    """
        Manage factories to handle creation of new samples.
    """

    def __init__(self):
        self.factory = SampleFactory()

    def run(self, *args, **kwargs):
        self.factory.new_sample(*args, **kwargs)

new_raw_sample_task = registry.tasks[EventRawSampleManager.name]


@task()
class JobFactoryManager(Task):
    """
        Manages factories handling Job creation.
    """

    def __init__(self):
        self.factory = JobFactory()

    def run(self, *args, **kwargs):
        self.factory.new_job(*args, **kwargs)

new_job_task = registry.tasks[JobFactoryManager.name]

settings.FLOW_DEFINITIONS += [
    (r'EventNewRawSample', new_raw_sample_task),
    (r'EventCreateNewJob', new_job_task),
]
