# Various methods making oDesk API usage more effortless by providing
# shortcut functions for simple tasks.
#
# Ciphertext referenced in various methods' documentation is a unique
# worker identifier similar to it's id. Currently there is no direct way to
# acquire worker's ciphertext other than from direct references in other people
# jobs.
#
# Getting oDesk API Client should be done when multiple API queries are needed
# or non-standard ones.
import odesk
import datetime
import math

from django.conf import settings
from django.template.loader import get_template
from django.template import Context

from urlannotator.main.models import Job
from urlannotator.crowdsourcing.models import OdeskJob, OdeskMetaJob
from urlannotator.crowdsourcing.tagasauris_helper import (init_tagasauris_job,
    TAGASAURIS_GATHER_SAMPLES_PER_JOB, get_split)

import logging
log = logging.getLogger(__name__)


def make_odesk_client(token, secret, test=False):
    if test:
        return make_test_client(token, secret)

    return odesk.Client(
        settings.ODESK_SERVER_KEY,
        settings.ODESK_SERVER_SECRET,
        oauth_access_token=token,
        oauth_access_token_secret=secret,
        auth='oauth',
    )


def make_test_client(token=None, secret=None):
    """
        Returns server-authenticated oDesk client.
    """
    return odesk.Client(
        settings.ODESK_SERVER_KEY,
        settings.ODESK_SERVER_SECRET,
        oauth_access_token=settings.ODESK_SERVER_TOKEN_KEY,
        oauth_access_token_secret=settings.ODESK_SERVER_TOKEN_SECRET,
        auth='oauth',
    )


def get_worker_name(ciphertext):
    """
        Returns oDesk worker's name with given `ciphertext`.
    """
    client = make_test_client()
    try:
        r = client.provider.get_provider(ciphertext)
        return r['dev_full_name']
    except:
        return None

# TODO: Proper category and subcategory name here.
NEW_JOB_CATEGORY = 'Sales & Marketing'
NEW_JOB_SUBCATEGORY = 'Other - Sales & Marketing'

# TODO: Proper job visibility
NEW_JOB_TYPE = 'hourly'
NEW_JOB_VISIBILITY = 'invite-only'
NEW_JOB_HOURLY_DURATION = 0

NEW_JOB_BUYER_TEAM_REFERENCE = '712189'
NEW_JOB_DURATION = datetime.timedelta(days=7)

ODESK_HIT_SPLIT = 20


def calculate_job_end_date():
    """
        Calculates job's expiry date.
    """
    date = datetime.datetime.now() + NEW_JOB_DURATION
    # Date in format mm-dd-yyyy, e.g. 06-30-2012
    return date.strftime('%m-%d-%Y')


def init_odesk_job(job):
    """
        Creates oDesk sample gathering job for our job.
    """
    init_tagasauris_job(job=job)
    create_sample_gather(job=job)


def check_odesk_job(job):
    """
        Checks an oDesk job for new worker applications.
    """
    client = make_odesk_client()
    response = client.hr.get_offers(
        buyer_team_reference=NEW_JOB_BUYER_TEAM_REFERENCE,
        job_reference=job.reference
    )
    print response


def get_reference(client):
    r = client.hr.get_companies()
    return r[0]['reference']


def get_voting_split(job):
    """
        Calculates number of workers to accept offers from to voting job.
    """
    # First calculate number of hits
    no_hits = math.ceil(float(job.no_of_urls) / settings.TAGASAURIS_VOTE_MEDIA_PER_HIT)

    # Second, get a square root of the split, floored. Why square root?
    # Because it has diminishing returns - the more work has to be done
    # the lower amount of worker has to be added in comparison to smaller-work
    # jobs.
    # In other works: we wont end up with sky-rocketed amount of workers
    # required to get all urls!
    split = math.sqrt(math.ceil(float(no_hits) / ODESK_HIT_SPLIT))
    return split


def _create_job(title, description, job):
    """
        Creates oDesk job with given title and description and returns it's
        reference.
    """
    try:
        token = job.account.odesk_token
        secret = job.account.odesk_secret
        client = make_odesk_client(token, secret)
        data = {
            'buyer_team__reference': get_reference(client),
            'title': title,
            'job_type': NEW_JOB_TYPE,
            'description': description,
            'duration': NEW_JOB_HOURLY_DURATION,
            'visibility': NEW_JOB_VISIBILITY,
            'category': NEW_JOB_CATEGORY,
            'end_date': calculate_job_end_date(),
            'subcategory': NEW_JOB_SUBCATEGORY,
        }

        response = client.hr.post_job(job_data=data)

        reference = response['job']['reference']
        return reference
    except:
        log.exception(
            '[oDesk] Error while creating job for job %d' % job.id
        )
        return None


def create_sample_gather(job, only_hit=False, *args, **kwargs):
    """
        Creates oDesk sample gathering job according from passed Job object.
    """
    context = {
        'samples_count': TAGASAURIS_GATHER_SAMPLES_PER_JOB,
        'job': job,
    }

    titleTemplate = get_template('odesk_meta_sample_gather_title.txt')
    descriptionTemplate = get_template('odesk_meta_sample_gather_description.txt')

    title = titleTemplate.render(Context(context))
    description = descriptionTemplate.render(Context(context))

    reference_meta = _create_job(title, description, job)
    if reference_meta:
        OdeskMetaJob.objects.create_sample_gather(job=job,
            reference=reference_meta, workers_to_invite=get_split(job))
    return reference_meta


def create_voting(job, only_hit=False, *args, **kwargs):
    job = Job.objects.get(id=job.id)

    context = {
        'job': job,
    }

    titleTemplate = get_template('odesk_meta_voting_title.txt')
    descriptionTemplate = get_template('odesk_meta_voting_description.txt')

    title = titleTemplate.render(Context(context))
    description = descriptionTemplate.render(Context(context))

    reference = _create_job(title, description, job)
    if reference:
        OdeskMetaJob.objects.create_voting(job=job, reference=reference,
            workers_to_invite=get_voting_split(job))
    return reference


def create_btm_gather(title, description, no_of_urls, job, only_hit=False, *args, **kwargs):
    """
        Creates oDesk BTM sample gathering job according from passed Job object.
    """
    reference_meta = _create_job(title, description, job)
    if reference_meta:
        OdeskMetaJob.objects.create_btm_gather(job=job,
            reference=reference_meta, workers_to_invite=get_split(job))
    return reference_meta


def create_btm_voting(job, only_hit=False):
    job = Job.objects.get(id=job.id)

    context = {
        'job': job,
    }

    titleTemplate = get_template('odesk_meta_btm_voting_title.txt')
    descriptionTemplate = get_template('odesk_meta_btm_voting_description.txt')

    title = titleTemplate.render(Context(context))
    description = descriptionTemplate.render(Context(context))

    reference = _create_job(title, description, job)
    if reference:
        OdeskMetaJob.objects.create_btm_voting(job=job, reference=reference,
            workers_to_invite=get_voting_split(job))
    return reference
