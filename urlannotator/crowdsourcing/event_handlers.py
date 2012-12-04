from celery import task, Task, registry
from django.conf import settings
from django.contrib.auth.models import User

from factories import VoteStorageFactory
from urlannotator.crowdsourcing.models import (BeatTheMachineSample,
    WorkerQualityVote, OdeskMetaJob)
from urlannotator.main.models import Job, Sample, Worker, LABEL_YES
from urlannotator.crowdsourcing.odesk_helper import (check_odesk_job,
    add_odesk_teams)
from urlannotator.crowdsourcing.job_handlers import get_job_handler
from urlannotator.tools.synchronization import singleton

import logging
log = logging.getLogger(__name__)


@task(ignore_result=True)
def initialize_external_job(job_id, *args, **kwargs):
    """
        Create external jobs when job has been initialized.
    """
    job = Job.objects.get(id=job_id)
    handler = get_job_handler(job)
    handler.init_job(**kwargs)


@task(ignore_result=True)
class VoteStorageManager(Task):
    """ Manage creation of vote storages for jobs.
    """

    def __init__(self):
        self.factory = VoteStorageFactory()

    def run(self, *args, **kwargs):
        self.factory.init_storage(*args, **kwargs)

initialize_quality = registry.tasks[VoteStorageManager.name]


@task(ignore_result=True)
def initialize_btm_job(job_id, topic, description, no_of_urls, **kwargs):
    """
        Initializes BTM task for given job.
    """
    job = Job.objects.get(id=job_id)
    handler = get_job_handler(job)
    handler.init_btm_gather(topic=topic, description=description,
        no_of_urls=no_of_urls)


@task(ignore_result=True)
def btm_send_to_human(sample_id, **kwargs):
    '''
        Updates appropriate BTM job with new sample.
    '''
    btm = BeatTheMachineSample.objects.get(id=sample_id)
    job = btm.job
    handler = get_job_handler(job)
    handler.update_btm(btm_samples=[btm])


@task(ignore_result=True)
def update_job_votes_gathered(sample_id, worker_id):
    sample = Sample.objects.filter(id=sample_id).select_related('job')
    if not sample:
        log.warning(
            'Tried updating votes gathered for not existant sample %d'
            % sample_id
        )
        return
    sample = sample[0]
    sample.update_votes_cache()
    sample.job.get_progress_votes(cache=False)

    worker = Worker.objects.get(id=worker_id)
    worker.get_votes_added_count_for_job(sample.job, cache=False)

    # Update top workers
    sample.job.get_top_workers(cache=False)


def _vote_on_new_sample(sample_id, job_id, vote_constructor):
    sample = Sample.objects.get(id=sample_id)
    worker = sample.get_source_worker()
    if not worker:
        return

    vote_constructor(worker=worker, sample=sample, label=LABEL_YES)


@task(ignore_result=True)
def vote_on_new_sample(sample_id, job_id):
    '''
        Creates a LABEL_YES vote on the brand-new sample by the sample sender.
    '''
    return _vote_on_new_sample(sample_id, job_id,
        WorkerQualityVote.objects.new_vote)


@task(ignore_result=True)
def vote_on_new_btm_sample(sample_id, job_id):
    '''
        Creates a LABEL_YES vote on the brand-new btm sample by the sample
        sender.
    '''
    return _vote_on_new_sample(sample_id, job_id,
        WorkerQualityVote.objects.new_btm_vote)


@task(ignore_result=True)
class OdeskJobMonitor(Task):
    def check_jobs(self, odesk_jobs):
        if not odesk_jobs:
            return

        for odesk_job in odesk_jobs:
            check_odesk_job(odesk_job)

    def check_sample_gathering(self):
        odesk_jobs = OdeskMetaJob.objects.get_active_sample_gathering()
        log.debug('[oDesk] Checking sample_gathering: %s' % odesk_jobs)
        self.check_jobs(odesk_jobs)

    def check_voting(self):
        odesk_jobs = OdeskMetaJob.objects.get_active_voting()
        log.debug('[oDesk] Checking voting: %s' % odesk_jobs)
        self.check_jobs(odesk_jobs)

    def check_btm_gather(self):
        odesk_jobs = OdeskMetaJob.objects.get_active_btm_gather()
        log.debug('[oDesk] Checking btm: %s' % odesk_jobs)
        self.check_jobs(odesk_jobs)

    def check_btm_voting(self):
        odesk_jobs = OdeskMetaJob.objects.get_active_btm_voting()
        log.debug('[oDesk] Checking btm voting: %s' % odesk_jobs)
        self.check_jobs(odesk_jobs)

    @singleton(name='odesk-job-monitor')
    def run(self, *args, **kwargs):
        self.check_sample_gathering()
        self.check_voting()
        self.check_btm_gather()
        self.check_btm_voting()

odesk_job_monitor = registry.tasks[OdeskJobMonitor.name]


@task(ignore_result=True)
def create_odesk_teams(user_id, **kwargs):
    user = User.objects.get(id=user_id)
    add_odesk_teams(user=user)

FLOW_DEFINITIONS = [
    (r'^EventNewJobInitializationDone$', initialize_external_job, settings.CELERY_LONGSCARCE_QUEUE),
    (r'^EventBTMStarted$', initialize_btm_job, settings.CELERY_LONGSCARCE_QUEUE),
    (r'^EventBTMSendToHuman$', btm_send_to_human, settings.CELERY_LONGSCARCE_QUEUE),
    (r'^EventNewVoteAdded$', update_job_votes_gathered),
    (r'^EventNewSample$', vote_on_new_sample),
    (r'^EventNewBTMSample$', vote_on_new_btm_sample),
    (r'^EventNewOdeskAssoc$', create_odesk_teams),
    (r'^OdeskJobMonitor$', odesk_job_monitor),
    # (r'^EventSampleGathertingHITChanged$', job_new_gathering_hit),
    # WIP: DSaS/GAL quality algorithms.
    # (r'^EventGoldSamplesDone$', initialize_quality),
]
