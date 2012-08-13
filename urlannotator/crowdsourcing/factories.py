import hashlib
import uuid

from django.conf import settings

from tagapi.api import TagasaurisClient

from urlannotator.crowdsourcing.models import TagasaurisJobs
from urlannotator.main.models import Job


TAGASAURIS_SAMPLE_GATHERER_WORKFLOW = 'sample_gather'
TAGASAURIS_VOTING_WORKFLOW = 'voting'


class ExternalJobsFactory(object):

    def initialize_job(self, job_id, *args, **kwargs):

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

            return ext_id, result

        # TODO: we can run it in tasks with proper polling/callback with info
        # of job creation status.
        sample_gatering_key, _ = create_job(c, job,
            TAGASAURIS_SAMPLE_GATHERER_WORKFLOW)
        voting_key, _ = create_job(c, job, TAGASAURIS_VOTING_WORKFLOW)

        # Our link to tagasauris jobs.
        TagasaurisJobs(
            urlannotator_job_id=job.id,
            sample_gatering_key=sample_gatering_key,
            voting_key=voting_key,
            beatthemachine_key=None
        ).save()
