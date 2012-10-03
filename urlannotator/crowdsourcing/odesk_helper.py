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

from django.conf import settings
from django.template.loader import get_template
from django.template import Context

from urlannotator.main.models import Job


def make_odesk_client():
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
    client = make_odesk_client()
    r = client.provider.get_provider(ciphertext)
    return r['dev_full_name']

# TODO: Proper category and subcategory name here.
NEW_JOB_CATEGORY = 'Sales & Marketing'
NEW_JOB_SUBCATEGORY = 'Other - Sales & Marketing'

# TODO: Proper job visibility
NEW_JOB_TYPE = 'fixed-price'
NEW_JOB_VISIBILITY = 'invite-only'

NEW_JOB_MINIMUM_BUDGET = 5.0

NEW_JOB_BUYER_TEAM_REFERENCE = '712189'


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


def create_odesk_job(job):
    """
        Creates oDesk job according from passed Job object.
    """
    # TODO: Add multiple job creations to cover whole number of samples to
    #       gather. As of now, only one person can be hired in a single job.
    job = Job.objects.get(id=job.id)
    client = make_odesk_client()

    context = {
        'samples_count': 5,
        'job': job,
    }

    titleTemplate = get_template('odesk_job_title.txt')
    descriptionTemplate = get_template('odesk_job_description.txt')

    data = {
        'buyer_team__reference': NEW_JOB_BUYER_TEAM_REFERENCE,
        'title': 'test',
        # 'title': titleTemplate.render(Context(context)),
        'job_type': NEW_JOB_TYPE,
        'description': 'test',
        # 'description': descriptionTemplate.render(Context(context)),
        'budget': calculate_single_budget(job=job),
        'visibility': NEW_JOB_VISIBILITY,
        'category': NEW_JOB_CATEGORY,
        'subcategory': NEW_JOB_SUBCATEGORY,
    }
    response = client.hr.post_job(job_data=data)

    print response