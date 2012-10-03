import hashlib
import uuid
import json

from django.conf import settings

from tagapi.api import TagasaurisClient
from urlannotator.crowdsourcing.models import TagasaurisJobs


def make_tagapi_client():
    return TagasaurisClient(settings.TAGASAURIS_LOGIN,
        settings.TAGASAURIS_PASS, settings.TAGASAURIS_HOST)


def sample_to_mediaobject(sample):
    ext_id = hashlib.md5(str(uuid.uuid4())).hexdigest()

    return {
        'id': ext_id,
        'title': ext_id,
        'mimetype': "image/png",
        'url': sample.screenshot,
    }


def samples_to_mediaobjects(samples):
    mediaobjects = {}
    for sample in samples:
        mediaobjects.update({sample: sample_to_mediaobject(sample)})

    return mediaobjects


def stop_job(external_id):
    tc = make_tagapi_client()
    res = tc.stop_job(external_id=external_id)
    tc.wait_for_complete(res['task_id'])


def create_tagasauris_job(job):
    """
        Initializes Tagasauris job for given our job.
    """
    # TODO: Need to add backoff on Tagasauris job creation fail.
    # TODO: we can run it in tasks with proper polling/callback with info
    # of job creation status.
    sample_gathering_key, sample_gathering_hit = create_job(
        job=job,
        task_type=settings.TAGASAURIS_SAMPLE_GATHERER_WORKFLOW,
        callback=settings.TAGASAURIS_SAMPLE_GATHERER_CALLBACK % job.id,
        api_client=make_tagapi_client(),
    )

    # Our link to tagasauris jobs.
    TagasaurisJobs.objects.create(
        urlannotator_job=job,
        sample_gathering_key=sample_gathering_key,
        sample_gathering_hit=sample_gathering_hit,
    )


def create_job(job, task_type, api_client=None, callback=None,
    mediaobjects=None):
    # Unique id for tagasauris job within our tagasauris account.
    ext_id = hashlib.md5(str(uuid.uuid4())).hexdigest()

    # Tagasauris Job is created with dummy media object (soo ugly...).
    # Before job creation we must configure Tagasauris account and
    # workflows. Account must have disabled billings & workflows need
    # to have "external" flag set.

    kwargs = {
        "id": ext_id,
        "title": job.title,
        "task": {
            "id": task_type,
            "instruction": job.description,
            "paid": "0.0",
            "keywords": ""
        },
        "workflow": {
            settings.TAGASAURIS_SURVEY[task_type]: {
                "config": {
                    "hit_instructions": job.description
                }
            },
        }
    }

    # Setting callback for notify mechanical task.
    if callback is not None:
        kwargs["workflow"].update({
            # NOTE: Here we can modify number of workers/media per hit but
            # i dont see use of it now.
            # settings.TAGASAURIS_SURVEY[task_type]: {
            #     "config": {
            #         "workers_per_hit": 1,
            #         "media_per_hit": 1,
            #     }
            # },
            settings.TAGASAURIS_NOTIFY[task_type]: {
                "config": {
                    "notify_url": callback
                }
            },
        })

    if task_type == settings.TAGASAURIS_SAMPLE_GATHERER_WORKFLOW:
        baseurl = settings.TAGASAURIS_CALLBACKS
        templates = baseurl + "/statics/js/templates/tagasauris/"
        kwargs["workflow"].update({
            settings.TAGASAURIS_FORM[task_type]: {
                "config": {
                    "external_app": json.dumps({
                        "external_js": [
                            baseurl + "/statics/js/tagasauris/samplegather.js"
                        ],
                        "external_css": [],
                        "external_data": {
                            "job_id": job.id,
                            "token": job.id,
                            "core_url": baseurl
                        },
                        "external_templates": {
                            "samplegather": templates + "samplegather.ejs",
                            "sample": templates + "sample.ejs"
                        }
                    })
                }
            },
        })

    # Choosing mediaobjects
    url = settings.DUMMY_URLANNOTATOR_URL
    if mediaobjects is None:
        kwargs.update({"dummy_media":
            [("dummy-" + str(no), url) for no in xrange(job.no_of_urls)]})
    else:
        kwargs.update({"mediaobjects": mediaobjects})

    result = api_client.create_job(**kwargs)

    # media_import_key = result[0]
    job_creation_key = result[1]
    api_client.wait_for_complete(job_creation_key)

    result = api_client.get_job(external_id=ext_id)
    hit = result['hits'][0] if result['hits'] else None

    return ext_id, hit
