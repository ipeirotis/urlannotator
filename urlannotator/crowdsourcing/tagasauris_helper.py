import hashlib
import uuid
import time

from django.conf import settings

from tagapi.api import TagasaurisClient


TAGASAURIS_SAMPLE_GATHERER_WORKFLOW = 'sample_gather'
TAGASAURIS_VOTING_WORKFLOW = 'voting'


def make_tagapi_client():
    return TagasaurisClient(settings.TAGASAURIS_LOGIN,
        settings.TAGASAURIS_PASS, settings.TAGASAURIS_HOST)


def sample_to_mediaobject(sample):
    ext_id = hashlib.md5(str(uuid.uuid4())).hexdigest()

    return {
        'id': ext_id,
        'mimetype': "image/png",
        'url': sample.screenshot,
    }


def samples_to_mediaobjects(samples):
    mediaobjects = {}
    for sample in samples:
        mediaobjects.update({sample: sample_to_mediaobject(sample)})

    return mediaobjects


def create_job(api_client, job, task_type, mediaobjects=None):
    # Unique id for tagasauris job within our tagasauris account.
    ext_id = hashlib.md5(str(uuid.uuid4())).hexdigest()

    # Tagasauris Job is created with dummy media object (soo ugly...).
    # Before job creation we must configure Tagasauris account and
    # workflows. Account must have disabled billings & workflows need
    # to have "external" flag set.
    if mediaobjects is None:
        result = api_client.create_job(
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
    else:
        result = api_client.create_job(
            id=ext_id,
            title=job.title,
            task={
                "id": task_type,
                "instruction": job.description,
                "paid": "0.0",
                "keywords": ""
            },
            mediaobjects=mediaobjects
        )

    # media_import_key = result[0]
    job_creation_key = result[1]
    api_client.wait_for_complete(job_creation_key)

    result = api_client.get_job(external_id=ext_id)
    hit = result['hits'][0]

    # Using hit later - example:
    # ext_url = settings.TAGASAURIS_HIT_URL % hit

    return ext_id, hit
