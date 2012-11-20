from urlannotator.crowdsourcing.quality.algorithms import (MajorityVoting,
    DBVotesStorage)
from urlannotator.main.models import Job
from urlannotator.crowdsourcing.troia_helper import init_troia

import logging
log = logging.getLogger(__name__)


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
