import hashlib
import uuid
import time

from django.conf import settings

from tagapi.api import TagasaurisClient

from urlannotator.crowdsourcing.models import TagasaurisJobs
from urlannotator.main.models import Job

import logging
log = logging.getLogger(__name__)


TAGASAURIS_SAMPLE_GATHERER_WORKFLOW = 'sample_gather'
TAGASAURIS_VOTING_WORKFLOW = 'voting'


class ExternalJobsFactory(object):

    def initialize_job(self, job_id, *args, **kwargs):
        if settings.TOOLS_TESTING:
            return

        job = Job.objects.get(id=job_id)

        c = TagasaurisClient(settings.TAGASAURIS_LOGIN,
            settings.TAGASAURIS_PASS, settings.TAGASAURIS_HOST)

        def create_job(c, job, task_type):
            # Unique id for tagasauris job within our tagasauris account.
            ext_id = hashlib.md5(str(uuid.uuid4())).hexdigest()

            # Tagasauris Job is created with dummy media object (soo ugly...).
            # Before job creation we must configure Tagasauris account and
            # workflows. Account must have disabled billings & workflows need
            # to have "external" flag set.
            result = c.create_job(
                id=ext_id,
                title=job.title,
                task={
                    "id": task_type,
                    "instruction": job.description,
                    "paid": "0.0",
                    "keywords": ""
                },
                dummy_media='dummy'
            )

            # media_import_key = result[0]
            job_creation_key = result[1]

            job_created = False
            while not job_created:
                time.sleep(5)
                res = c.status_progress(status_key=job_creation_key)
                job_created = res['completed'] == 100 and res['status'] == 'ok'

            result = c.get_job(external_id=ext_id)
            hit = result['hits'][0]

            # Using hit later - example:
            # ext_url = settings.TAGASAURIS_HIT_URL % hit

            return ext_id, hit

        # TODO: we can run it in tasks with proper polling/callback with info
        # of job creation status.
        sample_gathering_key, sample_gatering_hit = create_job(c, job,
            TAGASAURIS_SAMPLE_GATHERER_WORKFLOW)
        # voting_key, voting_hit = create_job(c, job, TAGASAURIS_VOTING_WORKFLOW)
        voting_key = 1
        voting_hit = None

        # Our link to tagasauris jobs.
        TagasaurisJobs(
            urlannotator_job=job,
            sample_gathering_key=sample_gatering_key,
            voting_key=voting_key,
            beatthemachine_key=None,
            sample_gatering_hit=sample_gatering_hit,
            voting_hit=voting_hit,
        ).save()
