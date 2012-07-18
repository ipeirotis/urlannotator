from celery import task, Task, registry


@task()
class EventRawSampleManager(Task):

    def __init__(self):
        pass

    def run(job, worker, url, label=''):
        pass

new_raw_sample_task = registry.tasks[EventRawSampleManager.name]


FLOW_DEFINITIONS = [
    (r'EventClassifierTrained', new_raw_sample_task),
]
