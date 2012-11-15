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

from django.conf import settings
from django.template.loader import get_template
from django.template import Context

from urlannotator.main.models import Job
from urlannotator.crowdsourcing.models import OdeskJob
from urlannotator.crowdsourcing.tagasauris_helper import init_tagasauris_job


def make_odesk_client(api_token=None):
    """
        Returns server-authenticated oDesk client.
    """
    if not api_token:
        return odesk.Client(
            settings.ODESK_SERVER_KEY,
            settings.ODESK_SERVER_SECRET,
            oauth_access_token=settings.ODESK_SERVER_TOKEN_KEY,
            oauth_access_token_secret=settings.ODESK_SERVER_TOKEN_SECRET,
            auth='oauth',
        )
    return odesk.Client(settings.ODESK_CLIENT_ID, settings.ODESK_CLIENT_SECRET,
        api_token=api_token)


def get_worker_name(ciphertext):
    """
        Returns oDesk worker's name with given `ciphertext`.
    """
    client = make_odesk_client()
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

NEW_JOB_MINIMUM_BUDGET = 5.0

NEW_JOB_BUYER_TEAM_REFERENCE = '712189'
NEW_JOB_DURATION = datetime.timedelta(days=7)


def calculate_single_budget(job):
    """
        Calculates oDesk job budget for a single worker.
    """
    # TODO: Proper budget calculation.
    if job.budget < NEW_JOB_MINIMUM_BUDGET:
        raise Exception(
            "oDesk API: New job minimum budget too small. "
            "Minimum %0.2f required." % NEW_JOB_MINIMUM_BUDGET
        )
    return NEW_JOB_MINIMUM_BUDGET


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
    create_voting(job=job)


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


def _create_job(title, description, job):
    """
        Creates oDesk job with given title and description and returns it's
        reference.
    """
    client = make_odesk_client(job.account.odesk_key)
    data = {
        'buyer_team__reference': NEW_JOB_BUYER_TEAM_REFERENCE,
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


def create_sample_gather(job):
    """
        Creates oDesk job according from passed Job object.
    """
    # TODO: Add multiple job creations to cover whole number of samples to
    #       gather. As of now, only one person can be hired in a single job.
    job = Job.objects.get(id=job.id)

    context = {
        'samples_count': 5,
        'job': job,
    }

    titleTemplate = get_template('odesk_sample_gather_title.txt')
    descriptionTemplate = get_template('odesk_sample_gather_description.txt')

    title = titleTemplate.render(Context(context))
    description = descriptionTemplate.render(Context(context))

    reference = _create_job(title, description, job)
    OdeskJob.objects.create_sample_gather(job=job, reference=reference)


def create_voting(job):
    # TODO: Add multiple job creations to cover whole number of samples to
    #       gather. As of now, only one person can be hired in a single job.
    job = Job.objects.get(id=job.id)

    context = {
        'samples_count': 5,
        'job': job,
    }

    titleTemplate = get_template('odesk_voting_title.txt')
    descriptionTemplate = get_template('odesk_voting_description.txt')

    title = titleTemplate.render(Context(context))
    description = descriptionTemplate.render(Context(context))

    reference = _create_job(title, description, job)
    OdeskJob.objects.create_voting(job=job, reference=reference)
