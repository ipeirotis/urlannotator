from urlannotator.crowdsourcing.models import TagasaurisJobs
from urlannotator.crowdsourcing.tagasauris_helper import (make_tagapi_client,
    create_sample_gather, create_btm)
from urlannotator.crowdsourcing.quality.algorithms import (MajorityVoting,
    DBVotesStorage)
from urlannotator.crowdsourcing.troia_helper import init_troia
from urlannotator.main.models import Job

import logging
log = logging.getLogger(__name__)


class ExternalJobsFactory(object):

    def initialize_job(self, job_id, *args, **kwargs):
        job = Job.objects.get(id=job_id)

        c = make_tagapi_client()

        sample_gathering_key, sample_gathering_hit = create_sample_gather(c,
            job)

        # Our link to tagasauris jobs.
        TagasaurisJobs.objects.create(
            urlannotator_job=job,
            sample_gathering_key=sample_gathering_key,
            sample_gathering_hit=sample_gathering_hit,
        )

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
