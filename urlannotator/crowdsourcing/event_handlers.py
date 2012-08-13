from celery import task, Task, registry

from tasks import send_validated_samples
from factories import ExternalJobsFactory


@task()
class SamplesValidationManager(Task):
    """ Manage validation of new samples and batches it for training classifier.
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
        send_validated_samples.delay(sample_id)

new_sample_task = registry.tasks[SamplesValidationManager.name]


@task()
class ExternalJobsManager(Task):
    """ Manage creation of external jobs creation.
    """

    def __init__(self):
        self.factory = ExternalJobsFactory()

    def run(self, *args, **kwargs):
        self.factory.initialize_job(*args, **kwargs)

initialize_external_jobs = registry.tasks[ExternalJobsManager.name]

FLOW_DEFINITIONS = [
    (r'^EventNewSample$', new_sample_task),
    (r'^EventNewJobInitialization$', initialize_external_jobs),
]
