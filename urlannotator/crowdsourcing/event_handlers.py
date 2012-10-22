from celery import task, Task, registry

from factories import ExternalJobsFactory, VoteStorageFactory


@task(ignore_result=True)
class ExternalJobsManager(Task):
    """ Manage creation of external jobs.
    """

    def __init__(self):
        self.factory = ExternalJobsFactory()

    def run(self, *args, **kwargs):
        self.factory.initialize_job(*args, **kwargs)

initialize_external_jobs = registry.tasks[ExternalJobsManager.name]


@task(ignore_result=True)
class VoteStorageManager(Task):
    """ Manage creation of vote storages for jobs.
    """

    def __init__(self):
        self.factory = VoteStorageFactory()

    def run(self, *args, **kwargs):
        self.factory.init_storage(*args, **kwargs)

initialize_quality = registry.tasks[VoteStorageManager.name]


@task(ignore_result=True)
class BTMJobsManager(Task):
    """ Manage creation of BTM jobs.
    """

    def __init__(self):
        self.factory = ExternalJobsFactory()

    def run(self, *args, **kwargs):
        self.factory.initialize_btm(*args, **kwargs)

initialize_btm_job = registry.tasks[BTMJobsManager.name]


FLOW_DEFINITIONS = [
    (r'^EventNewJobInitialization$', initialize_external_jobs),
    (r'^EventBTMStarted$', initialize_btm_job),
    # WIP: DSaS/GAL quality algorithms.
    # (r'^EventGoldSamplesDone$', initialize_quality),
]
