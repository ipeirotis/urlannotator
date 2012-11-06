from urlannotator.crowdsourcing.tagasauris_helper import (create_tagasauris_job,
    make_tagapi_client, create_btm)
from urlannotator.crowdsourcing.odesk_helper import create_odesk_job
from urlannotator.crowdsourcing.quality.algorithms import (MajorityVoting,
    DBVotesStorage)
from urlannotator.main.models import (Job, JOB_SOURCE_ODESK_FREE,
    JOB_SOURCE_ODESK_PAID, JOB_SOURCE_OWN_WORKFORCE)
from urlannotator.crowdsourcing.models import TagasaurisJobs
from urlannotator.crowdsourcing.troia_helper import init_troia

import logging
log = logging.getLogger(__name__)


def unsupported_job(job, *args, **kwargs):
    raise Exception(
        'Unsupported external job initializer for source %s.' % job.data_source
    )


def odesk_initializer(job, *args, **kwargs):
    create_tagasauris_job(job=job)
    create_odesk_job(job=job)


def own_workforce_initializer(job, *args, **kwargs):
    create_tagasauris_job(job=job)


job_initializers = {
    JOB_SOURCE_OWN_WORKFORCE: own_workforce_initializer,
    JOB_SOURCE_ODESK_PAID: odesk_initializer,
    JOB_SOURCE_ODESK_FREE: odesk_initializer,
}


class ExternalJobsFactory(object):
    """
        Handles initialization of external jobs tied to new job's data source.

        If you want to add new data sources, you need to at least specify
        initializer method inside `job_initializers`.
        The initializer method is passed a `job` Job object which is the new
        job being created.
    """

    def get_initializer(self, job):
        return job_initializers.get(job.data_source, unsupported_job)

    def initialize_job(self, job_id, *args, **kwargs):
        """
            Handles creating any external jobs for given our job's id.
        """
        job = Job.objects.get(id=job_id)

        initializer = self.get_initializer(job=job)
        initializer(job=job)

    def initialize_btm(self, job_id, topic, description, no_of_urls):
        job = Job.objects.get(id=job_id)

        c = make_tagapi_client()

        beatthemachine_key, beatthemachine_hit = create_btm(c, job, topic,
            description, no_of_urls)

        # Our link to tagasauris jobs.
        tj, _ = TagasaurisJobs.objects.get_or_create(urlannotator_job=job)
        tj.beatthemachine_key = beatthemachine_key
        tj.beatthemachine_hit = beatthemachine_hit
        tj.save()


class VoteStorageFactory(object):
    """
        Initializes votes' storage for new jobs.
    """
    initializers = {
        'TroiaVotesStorage': init_troia,
    }

    def _default_initializer(self, job):
        pass

    def init_storage(self, job_id):
        job = Job.objects.get(id=job_id)
        storage = job.votes_storage
        init = self.initializers.get(storage, self._default_initializer)
        init(job=job)


class QualityAlgorithmFactory(object):

    def create_algorithm(self, job, *args, **kwargs):
        return MajorityVoting(
            job_id=job.id,
            votes_storage=DBVotesStorage(storage_id=job.id)
        )

quality_factory = QualityAlgorithmFactory()
