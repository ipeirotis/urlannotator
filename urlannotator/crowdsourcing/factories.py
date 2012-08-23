from django.conf import settings

from urlannotator.crowdsourcing.models import TagasaurisJobs
from urlannotator.crowdsourcing.tagasauris_helper import (make_tagapi_client,
    create_job, TAGASAURIS_SAMPLE_GATHERER_WORKFLOW)
from urlannotator.main.models import Job

import logging
log = logging.getLogger(__name__)


class ExternalJobsFactory(object):

    def initialize_job(self, job_id, *args, **kwargs):
        if settings.TOOLS_TESTING:
            return

        job = Job.objects.get(id=job_id)

        c = make_tagapi_client()

        # TODO: we can run it in tasks with proper polling/callback with info
        # of job creation status.
        sample_gathering_key, sample_gathering_hit = create_job(c, job,
            TAGASAURIS_SAMPLE_GATHERER_WORKFLOW)

        # We no longer want to create voting instantly after job start.
        # voting_key, voting_hit = create_job(c, job, TAGASAURIS_VOTING_WORKFLOW)

        # Our link to tagasauris jobs.
        TagasaurisJobs(
            urlannotator_job=job,
            sample_gathering_key=sample_gathering_key,
            sample_gatering_hit=sample_gathering_hit,
        ).save()
