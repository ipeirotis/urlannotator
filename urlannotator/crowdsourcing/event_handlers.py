from celery import task, Task, registry

from factories import ExternalJobsFactory


@task(ignore_result=True)
class ExternalJobsManager(Task):
    """ Manage creation of external jobs creation.
    """

    def __init__(self):
        self.factory = ExternalJobsFactory()

    def run(self, *args, **kwargs):
        self.factory.initialize_job(*args, **kwargs)

initialize_external_jobs = registry.tasks[ExternalJobsManager.name]

FLOW_DEFINITIONS = [
    (r'^EventNewJobInitialization$', initialize_external_jobs),
]
