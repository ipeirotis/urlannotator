from celery import task, Task, registry
from factories import SampleFactory


@task()
class EventRawSampleManager(Task):
    """ Manage factories to handle creation of new samples.
    """

    def __init__(self):
        self.factory = SampleFactory()

    def run(self, job, worker, url, label=''):
        self.factory.new_sample(job, worker, url, label)

new_raw_sample_task = registry.tasks[EventRawSampleManager.name]


FLOW_DEFINITIONS = [
    (r'EventNewRawSample', new_raw_sample_task),
]
