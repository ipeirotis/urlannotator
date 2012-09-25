import hashlib
import uuid

from django.conf import settings

from tagapi.api import TagasaurisClient


EXTERNAL_SAMPLE_GATHER_APP = {
    "external_js": [
        "http://127.0.0.1:8000/statics/js/tagasauris/samplegather.js"],
    "external_css": [],
    "external_data": {
        "token": "3456",
        "core_url": "http://127.0.0.1:8000"
    },
    "external_templates": {
        "samplegather": "http://127.0.0.1:8000/statics/js/templates/tagasauris/samplegather.ejs"
    }
}


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


def create_job(api_client, job, task_type, callback=None, mediaobjects=None):
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

    # Choosing mediaobjects
    if mediaobjects is None:
        kwargs.update({"dummy_media":
            ["dummy-" + str(no) for no in xrange(job.no_of_urls)]})
    else:
        kwargs.update({"mediaobjects": mediaobjects})

    result = api_client.create_job(**kwargs)

    # media_import_key = result[0]
    job_creation_key = result[1]
    api_client.wait_for_complete(job_creation_key)

    result = api_client.get_job(external_id=ext_id)
    hit = result['hits'][0] if result['hits'] else None

    return ext_id, hit
