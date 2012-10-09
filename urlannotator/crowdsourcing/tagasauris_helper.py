import hashlib
import uuid
import json
import math

from django.conf import settings

from tagapi.api import TagasaurisClient


def make_tagapi_client():
    return TagasaurisClient(settings.TAGASAURIS_LOGIN,
        settings.TAGASAURIS_PASS, settings.TAGASAURIS_HOST)


def make_external_id():
    return hashlib.md5(str(uuid.uuid4())).hexdigest()


def sample_to_mediaobject(sample):
    ext_id = make_external_id()

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


def workflow_definition(ext_id, job, task_type, survey_id):
    return {
        "id": ext_id,
        "title": job.title,
        "task": {
            "id": task_type,
            "instruction": job.description,
            "paid": "0.0",
            "keywords": ""
        },
        "workflow": {
            survey_id: {
                "config": {
                    "hit_type": settings.TAGASAURIS_HIT_TYPE,
                    "hit_title": "Gather samples for \"%s\"" % job.title,
                    # "workers_per_hit": "1",
                    # "price": "0.08",
                    # "job_external_id": "yes",
                    # "hit_description": "Gather samples",
                    "hit_instructions": job.description,
                    # "media_per_hit": "1",
                }
            },
        }
    }


def create_sample_gather(api_client, job):
    task_type = settings.TAGASAURIS_SAMPLE_GATHERER_WORKFLOW
    # Unique id for tagasauris job within our tagasauris account.
    ext_id = make_external_id()

    # Tagasauris Job is created with dummy media object (soo ugly...).
    # Before job creation we must configure Tagasauris account and
    # workflows. Account must have disabled billings & workflows need
    # to have "external" flag set.

    kwargs = workflow_definition(ext_id, job, task_type,
        settings.TAGASAURIS_SURVEY[task_type])

    samples_per_job = 5
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
                        "core_url": baseurl,
                        "min_samples": samples_per_job,
                    },
                    "external_templates": {
                        "samplegather": templates + "samplegather.ejs",
                        "sample": templates + "sample.ejs"
                    }
                })
            }
        },
    })

    total_mediaobjects = math.ceil(float(job.no_of_urls) / samples_per_job)
    url = settings.DUMMY_URLANNOTATOR_URL
    kwargs.update({"dummy_media":
        [("dummy", url) for no in xrange(int(total_mediaobjects))]})

    return _create_job(api_client, ext_id, kwargs)


def create_btm(api_client, job):
    task_type = settings.TAGASAURIS_SAMPLE_GATHERER_WORKFLOW
    # Unique id for tagasauris job within our tagasauris account.
    ext_id = make_external_id()

    # Tagasauris Job is created with dummy media object (soo ugly...).
    # Before job creation we must configure Tagasauris account and
    # workflows. Account must have disabled billings & workflows need
    # to have "external" flag set.

    kwargs = workflow_definition(ext_id, job, task_type,
        settings.TAGASAURIS_SURVEY[task_type])

    samples_per_job = 5
    baseurl = settings.TAGASAURIS_CALLBACKS
    templates = baseurl + "/statics/js/templates/tagasauris/"
    kwargs["workflow"].update({
        settings.TAGASAURIS_FORM[task_type]: {
            "config": {
                "external_app": json.dumps({
                    "external_js": [
                        baseurl + "/statics/js/tagasauris/btm.js"
                    ],
                    "external_css": [],
                    "external_data": {
                        "job_id": job.id,
                        "token": job.id,
                        "core_url": baseurl,
                        "min_samples": samples_per_job,
                    },
                    "external_templates": {
                        "samplegather": templates + "btm.ejs",
                        "sample": templates + "btm_sample.ejs"
                    }
                })
            }
        },
    })

    # TODO: check how may btm should be running?
    total_mediaobjects = 5
    url = settings.DUMMY_URLANNOTATOR_URL
    kwargs.update({"dummy_media":
        [("dummy", url) for no in xrange(int(total_mediaobjects))]})

    return _create_job(api_client, ext_id, kwargs)


def create_voting(api_client, job, mediaobjects):
    task_type = settings.TAGASAURIS_VOTING_WORKFLOW

    # Unique id for tagasauris job within our tagasauris account.
    ext_id = make_external_id()

    # Tagasauris Job is created with dummy media object (soo ugly...).
    # Before job creation we must configure Tagasauris account and
    # workflows. Account must have disabled billings & workflows need
    # to have "external" flag set.

    kwargs = workflow_definition(ext_id, job, task_type,
        settings.TAGASAURIS_SURVEY[task_type])

    # Setting callback for notify mechanical task.
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
                "notify_url": settings.TAGASAURIS_VOTING_CALLBACK % job.id
            }
        },
    })

    # Choosing mediaobjects
    kwargs.update({"mediaobjects": mediaobjects})

    return _create_job(api_client, ext_id, kwargs)


def _create_job(api_client, ext_id, kwargs):
    result = api_client.create_job(**kwargs)

    # media_import_key = result[0]
    job_creation_key = result[1]
    api_client.wait_for_complete(job_creation_key)

    result = api_client.get_job(external_id=ext_id)

    if settings.TAGASAURIS_HIT_TYPE == settings.TAGASAURIS_MTURK:
        hit_type = 'external_id'
    else:
        hit_type = 'mturk_group_id'

    hit = result['hits'][0][hit_type] if result['hits'] else None

    return ext_id, hit
