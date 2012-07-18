from django.conf import settings

from celery import task, Task, registry

from tasks import send_validated_samples


@task()
class SamplesValidationManager(Task):
    """ Manage factories to handle creation of new samples.
    """

    def __init__(self):
        self.samples = []

    def run(self, sample_id, *args, **kwargs):
        # FIXME: Mock
        # TODO: validation part, batching etc...
        self.samples.append(sample_id)

        # FIXME: Mock
        # TODO: Later after more samples are collected we launch
        # send_validated_samples
        send_validated_samples.delay(self.samples)

new_sample_task = registry.tasks[SamplesValidationManager.name]


settings.FLOW_DEFINITIONS += [
    (r'EventNewSample', new_sample_task),
]
