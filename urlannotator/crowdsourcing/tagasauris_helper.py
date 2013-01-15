import hashlib
import uuid
import json
import math

from django.conf import settings
from itertools import imap
from tagapi.api import TagasaurisClient
from tagapi.error import TagasaurisApiException, TagasaurisApiMaxRetries
from urlannotator.tools.utils import setting

import logging
log = logging.getLogger(__name__)

TAGASAURIS_CALLBACKS = setting('TAGASAURIS_CALLBACKS',
    'http://' + settings.SITE_URL)
TAGASAURIS_VOTING_CALLBACK = setting('TAGASAURIS_VOTING_CALLBACK',
    TAGASAURIS_CALLBACKS + '/api/v1/vote/add/tagasauris/%s/')
TAGASAURIS_BTM_VOTING_CALLBACK = setting('TAGASAURIS_BTM_VOTING_CALLBACK',
    TAGASAURIS_CALLBACKS + '/api/v1/vote/btm/tagasauris/%s/')

# Tagasauris needs sacrifice!
DUMMY_URLANNOTATOR_URL = setting('DUMMY_URLANNOTATOR_URL',
    'http://' + settings.SITE_URL + '/statics/img/favicon.png')

TAGASAURIS_HIT_SOCIAL_URL = setting('TAGASAURIS_HIT_SOCIAL_URL',
    settings.TAGASAURIS_HOST + '/actions/start_annotation/?hid=%s')

TAGASAURIS_GATHER_SAMPLES_PER_JOB = setting(
    'TAGASAURIS_GATHER_SAMPLES_PER_JOB', 5)

TAGASAURIS_GOAL_MULTIPLICATION = setting(
    'TAGASAURIS_GOAL_MULTIPLICATION', 1.2)


def get_hit_url(hit_type):
    if hit_type == settings.TAGASAURIS_SOCIAL:
        return TAGASAURIS_HIT_SOCIAL_URL
    elif hit_type == settings.TAGASAURIS_MTURK:
        return settings.TAGASAURIS_HIT_MTURK_URL
    return settings.TAGASAURIS_HIT_URL


def make_tagapi_client():
    return TagasaurisClient(settings.TAGASAURIS_LOGIN,
        settings.TAGASAURIS_PASS, settings.TAGASAURIS_HOST)


def make_external_id():
    return hashlib.md5(str(uuid.uuid4())).hexdigest()


def sample_to_mediaobject(sample, caption=""):
    ext_id = make_external_id()

    return {
        'id': ext_id,
        'title': ext_id,
        'mimetype': "image/png",
        'url': sample.screenshot,
        "attributes": {
            "caption": caption,
        }
    }


def samples_to_mediaobjects(samples, caption=""):
    mediaobjects = {}
    for sample in samples:
        if not sample.screenshot:
            log.critical(
                'samples_to_mediaobjects: sample %d has no url, '
                'skipping.' % sample.id)
            continue
        mediaobjects.update({sample: sample_to_mediaobject(sample, caption)})

    return mediaobjects


def stop_job(external_id):
    tc = make_tagapi_client()
    res = tc.stop_job(external_id=external_id)
    tc.wait_for_complete(res['task_id'])


def get_gather_goal(no_of_urls):
    return math.ceil(no_of_urls * TAGASAURIS_GOAL_MULTIPLICATION /
        TAGASAURIS_GATHER_SAMPLES_PER_JOB)


def get_gather_cost(no_of_urls):
    return get_gather_goal(no_of_urls) * float(
        settings.TAGASAURIS_GATHER_PRICE)


def get_split(job):
    gather_goal = get_gather_goal(job.no_of_urls)
    return math.ceil(math.sqrt(gather_goal))


def get_vote_cost(no_of_urls):
    return no_of_urls * TAGASAURIS_GOAL_MULTIPLICATION *\
        float(settings.TAGASAURIS_VOTE_WORKERS_PER_HIT) *\
        float(settings.TAGASAURIS_VOTE_PRICE) /\
        float(settings.TAGASAURIS_VOTE_MEDIA_PER_HIT)


def init_tagasauris_job(job):
    """
        Initializes Tagasauris sample_gathering job for given our job.
    """
    from urlannotator.crowdsourcing.models import TagasaurisJobs
    # TODO: Need to add backoff on Tagasauris job creation fail.
    # TODO: we can run it in tasks with proper polling/callback with info
    # of job creation status.
    sample_gathering_key, sample_gathering_hit = create_sample_gather(
        job=job,
        api_client=make_tagapi_client(),
    )

    if not sample_gathering_key:
        return False

    # Our link to tagasauris jobs.
    TagasaurisJobs.objects.create(
        urlannotator_job=job,
        sample_gathering_key=sample_gathering_key,
    )
    return True


def workflow_definition(ext_id, job, task_type, survey_id, price,
        hit_title="%s", workers_per_hit=1, media_per_hit=1,
        hit_instructions=None, topic=None, description=None, labels=[]):

    if hit_instructions is None:
        hit_instructions = job.description if description is None else description

    topic = job.title if topic is None else topic
    description = job.description if description is None else description

    return {
        "id": ext_id,
        "title": topic,
        "task": {
            "id": task_type,
            "instruction": description,
            "paid": "0.0",
            "keywords": ""
        },
        "workflow": {
            survey_id: {
                "config": {
                    "hit_type": job.get_hit_type(),
                    "hit_title": hit_title % topic,
                    "workers_per_hit": workers_per_hit,
                    "price": price,
                    # "job_external_id": "yes",
                    # "hit_description": "Gather samples",
                    "hit_instructions": hit_instructions,
                    "media_per_hit": media_per_hit,
                }
            },
        },
        "mturk_config": {
            "qualifications": [
                {
                    "compare_to": "60",
                    "type": "hit_approval_rate",
                    "comparator": "greater_or_equal_to"
                }
            ],
        },
        "labels": ["URLAnnotator"] + labels
    }


def create_sample_gather(api_client, job):
    task_type = settings.TAGASAURIS_SAMPLE_GATHERER_WORKFLOW
    # Unique id for tagasauris job within our tagasauris account.
    ext_id = make_external_id()

    # Compute split of tasks per mediaobjects and workers.
    workers_per_hit = get_split(job)
    total_mediaobjects = get_split(job)

    # Tagasauris Job is created with dummy media object (soo ugly...).
    # Before job creation we must configure Tagasauris account and
    # workflows. Account must have disabled billings & workflows need
    # to have "external" flag set.

    kwargs = workflow_definition(ext_id, job, task_type,
        settings.TAGASAURIS_SURVEY[task_type],
        settings.TAGASAURIS_GATHER_PRICE,
        hit_title="Gather web page urls for \"%s\"",
        workers_per_hit=workers_per_hit)

    baseurl = TAGASAURIS_CALLBACKS
    templates = baseurl + "/statics/js/templates/tagasauris/"
    kwargs["workflow"].update({
        settings.TAGASAURIS_FORM[task_type]: {
            "config": {
                "instruction_url": settings.TAGASAURIS_GATHER_INSTRUCTION_URL,
                "external_app": json.dumps({
                    "external_js": [
                        baseurl + "/statics/js/tagasauris/core.js",
                        baseurl + "/statics/js/tagasauris/samplegather.js"
                    ],
                    "external_css": [],
                    "external_data": {
                        "job_id": job.id,
                        "token": job.id,
                        "core_url": baseurl,
                        "min_samples": TAGASAURIS_GATHER_SAMPLES_PER_JOB,
                    },
                    "external_templates": {
                        "samplegather": templates + "samplegather.ejs",
                        "sample": templates + "sample.ejs"
                    }
                })
            }
        },
    })

    url = DUMMY_URLANNOTATOR_URL
    kwargs.update({"dummy_media":
        [("dummy-" + str(no), url) for no in xrange(int(total_mediaobjects))]})

    return _create_job(api_client, ext_id, job.get_hit_type(), kwargs)


def create_btm(api_client, job, topic, description, no_of_urls):
    task_type = settings.TAGASAURIS_SAMPLE_GATHERER_WORKFLOW
    # Unique id for tagasauris job within our tagasauris account.
    ext_id = make_external_id()

    # Tagasauris Job is created with dummy media object (soo ugly...).
    # Before job creation we must configure Tagasauris account and
    # workflows. Account must have disabled billings & workflows need
    # to have "external" flag set.

    # Compute split of tasks per mediaobjects and workers.
    workers_per_hit = get_split(job)
    total_mediaobjects = get_split(job)

    kwargs = workflow_definition(ext_id, job, task_type,
        settings.TAGASAURIS_SURVEY[task_type],
        settings.TAGASAURIS_BTM_PRICE,
        hit_title="Beat the Machine for \"%s\"",
        workers_per_hit=workers_per_hit,
        topic=topic,
        description=description,
        labels=["BTM", ])

    baseurl = TAGASAURIS_CALLBACKS
    templates = baseurl + "/statics/js/templates/tagasauris/"
    kwargs["workflow"].update({
        settings.TAGASAURIS_FORM[task_type]: {
            "config": {
                "external_app": json.dumps({
                    "external_js": [
                        baseurl + "/statics/js/tagasauris/core.js",
                        baseurl + "/statics/js/tagasauris/btm.js"
                    ],
                    "external_css": [],
                    "external_data": {
                        "job_id": job.id,
                        "token": job.id,
                        "core_url": baseurl,
                        "min_samples": TAGASAURIS_GATHER_SAMPLES_PER_JOB,
                    },
                    "external_templates": {
                        "btm": templates + "btm.ejs",
                        "btm_sample": templates + "btm_sample.ejs"
                    }
                })
            }
        },
    })

    # TODO: check how may btm should be running?
    url = DUMMY_URLANNOTATOR_URL
    kwargs.update({"dummy_media":
        [("dummy-" + str(no), url) for no in xrange(int(total_mediaobjects))]})

    return _create_job(api_client, ext_id, job.get_hit_type(), kwargs)


def _create_voting(api_client, job, mediaobjects, notify_url, topic=None,
        labels=[]):
    task_type = settings.TAGASAURIS_VOTING_WORKFLOW

    # Unique id for tagasauris job within our tagasauris account.
    ext_id = make_external_id()

    # Tagasauris Job is created with dummy media object (soo ugly...).
    # Before job creation we must configure Tagasauris account and
    # workflows. Account must have disabled billings & workflows need
    # to have "external" flag set.

    kwargs = workflow_definition(ext_id, job, task_type,
        settings.TAGASAURIS_SURVEY[task_type],
        settings.TAGASAURIS_VOTE_PRICE,
        hit_title="Verify web page urls from \"%s\"",
        workers_per_hit=settings.TAGASAURIS_VOTE_WORKERS_PER_HIT,
        media_per_hit=settings.TAGASAURIS_VOTE_MEDIA_PER_HIT,
        hit_instructions=settings.TAGASAURIS_VOTING_INSTRUCTION_URL,
        topic=topic,
        labels=labels)

    # Setting callback for notify mechanical task.
    kwargs["workflow"].update({
        settings.TAGASAURIS_NOTIFY[task_type]: {
            "config": {
                "notify_url": notify_url
            }
        },
    })

    # Choosing mediaobjects
    kwargs.update({"mediaobjects": mediaobjects})

    return _create_job(api_client, ext_id, job.get_hit_type(), kwargs)


def create_voting_job(api_client, job, samples):
    res = create_voting(api_client, job, samples, 'voting',
        notify_url=TAGASAURIS_VOTING_CALLBACK % job.id)
    return res


def create_btm_voting_job(api_client, job, samples):
    res = create_voting(api_client, job, samples, 'voting_btm',
        notify_url=TAGASAURIS_BTM_VOTING_CALLBACK % job.id,
        topic=job.btm_title,
        labels=["BTM"])
    return res


def create_voting(api_client, job, samples, field_name,
        notify_url, topic=None, labels=[]):
    from urlannotator.crowdsourcing.models import SampleMapping
    mediaobjects = samples_to_mediaobjects(samples, caption=job.description)

    # Objects to send.
    mo_values = mediaobjects.values()

    # Creating new job  with mediaobjects
    key, hit = _create_voting(api_client, job, mo_values,
        notify_url=notify_url, topic=topic, labels=labels)

    # Job creation failed (maximum retries exceeded or other error)
    if not key:
        return False

    setattr(job.tagasaurisjobs, '%s_key' % field_name, key)
    job.tagasaurisjobs.save()

    # ALWAYS add mediaobject mappings assuming Tagasauris will handle them
    # TODO: possibly check mediaobject status?
    for sample, mediaobject in mediaobjects.items():
        SampleMapping(
            sample=sample,
            external_id=mediaobject['id'],
            crowscourcing_type=SampleMapping.TAGASAURIS,
        ).save()

    return True


def update_voting(api_client, job, samples):
    log.info('Tagasauris: Updating voting job for job %d' % job.id)
    res = _update_voting(api_client, job, samples, 'voting')
    if res:
        log.info('Tagasauris: Updated voting job for job %d' % job.id)
    return res


def update_btm(api_client, job, samples):
    log.info('Tagasauris: Updating voting job for job %d' % job.id)
    res = _update_voting(api_client, job, samples, 'voting_btm')
    if res:
        log.info('Tagasauris: Updated voting job for job %d' % job.id)
    return res


def _update_voting(api_client, job, samples, field_name):
    from urlannotator.crowdsourcing.models import SampleMapping
    # Creates sample to mediaobject mapping
    mediaobjects = samples_to_mediaobjects(samples,
        caption=job.description)

    for sample, mediaobject in mediaobjects.items():
        SampleMapping(
            sample=sample,
            external_id=mediaobject['id'],
            crowscourcing_type=SampleMapping.TAGASAURIS,
        ).save()

    # New objects
    mediaobjects = mediaobjects.values()

    key = getattr(job.tagasaurisjobs, '%s_key' % field_name)
    hit = getattr(job.tagasaurisjobs, '%s_hit' % field_name)

    res = update_voting_job(api_client, mediaobjects, key)

    # If updating was failed - delete created. Why not create them here?
    # Because someone might have completed a HIT in the mean time, and we
    # would lose that info.
    if not res:
        SampleMapping.objects.filter(
            external_id__in=imap(lambda x: x['id'], mediaobjects)
        ).delete()

    # In case if tagasauris job was created without screenshots earlier.
    if hit is None:
        result = api_client.get_job(external_id=key)
        if not result:
            return True
        try:
            hit = result['hits'][0] if result['hits'] else None
            if hit is not None:
                setattr(job.tagasaurisjobs, '%s_hit' % field_name, hit)
                job.tagasaurisjobs.save()
        except:
            log.exception(
                'Tagasauris: Error while getting voting hit for job' % job.id
            )
            return True


def get_hit(api_client, job_ext_id, hit_type):
    try:
        result = api_client.get_job(external_id=job_ext_id)
        if hit_type == settings.TAGASAURIS_MTURK:
            hit_type = 'mturk_group_id'
        else:
            hit_type = 'external_id'

        hit = result['hits'][0][hit_type] if result['hits'] else None
        return hit
    except:
        log.exception(
            'Error while getting hit for job %s' % job_ext_id
        )
        return None


def update_voting_job(api_client, mediaobjects, ext_id):
    try:
        res = api_client.mediaobject_send(mediaobjects)
        api_client.wait_for_complete(res)

        res = api_client.job_add_media(
            external_ids=[mo['id'] for mo in mediaobjects],
            external_id=ext_id
        )

        # Make sure that tagasauris job is running (if not - restart it!)
        job_info = api_client.get_job(external_id=ext_id)
        if job_info['state'] == 'finished':
            api_client.restart_job(external_id=ext_id)
            # api_client.wait_for_complete(res['task_id'])

        return True
    except TagasaurisApiException, e:
        log.exception('Failed to update Tagasauris voting job: %s, %s' % (e, e.response))
        return False
    except Exception, e:
        log.exception('Failed to update Tagasauris voting job: %s' % e)
        return False


def _create_job(api_client, ext_id, hit_type, kwargs):
    try:
        result = api_client.create_job(**kwargs)

        # media_import_key = result[0]
        job_creation_key = result[1]
        api_client.wait_for_complete(job_creation_key)
        hit = get_hit(api_client, ext_id, hit_type)
        return ext_id, hit
    except TagasaurisApiMaxRetries, e:
        log.exception('Error while creating job: %s, %s' % (e, e.response))
        # Failed to wait for job's completion - return no id and retry later.
        return None, None
    except TagasaurisApiException, e:
        log.exception('Error while creating job: %s, %s' % (e, e.response))
        # Failed to get info about Tagasauris job - return None as hit
        return ext_id, None
    except Exception, e:
        log.exception('Error while creating job: %s' % e)
        # Failed to get info about Tagasauris job - return None as hit
        return ext_id, None
