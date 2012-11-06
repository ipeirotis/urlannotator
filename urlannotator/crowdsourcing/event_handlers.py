from itertools import imap

from celery import task, Task, registry
from django.conf import settings

from factories import ExternalJobsFactory, VoteStorageFactory
from urlannotator.crowdsourcing.models import (BeatTheMachineSample,
    TagasaurisJobs, SampleMapping, WorkerQualityVote)
from urlannotator.main.models import Sample, Worker, LABEL_YES
from urlannotator.crowdsourcing.tagasauris_helper import (create_btm_voting,
    samples_to_mediaobjects, make_tagapi_client, update_voting_job)

import logging
log = logging.getLogger(__name__)


@task(ignore_result=True)
class ExternalJobsManager(Task):
    """ Manage creation of external jobs.
    """

    def __init__(self):
        self.factory = ExternalJobsFactory()

    def run(self, *args, **kwargs):
        self.factory.initialize_job(*args, **kwargs)

initialize_external_jobs = registry.tasks[ExternalJobsManager.name]


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
class BTMJobsManager(Task):
    """ Manage creation of BTM jobs.
    """

    def __init__(self):
        self.factory = ExternalJobsFactory()

    def run(self, *args, **kwargs):
        self.factory.initialize_btm(*args, **kwargs)

initialize_btm_job = registry.tasks[BTMJobsManager.name]


@task(ignore_result=True)
def btm_send_to_human(sample_id):
    tc = make_tagapi_client()

    btm = BeatTheMachineSample.objects.get(id=sample_id)
    sample = btm.sample
    job = btm.job

    tag_jobs = TagasaurisJobs.objects.get(urlannotator_job=job)

    if not tag_jobs.voting_btm_key:
        # Creates sample to mediaobject mapping
        mediaobjects = samples_to_mediaobjects([sample, ],
            caption=job.description)

        # Objects to send.
        mo_values = mediaobjects.values()

        # Creating new job  with mediaobjects
        voting_btm_key, voting_btm_hit = create_btm_voting(tc, job, mo_values)

        # Job creation failed (maximum retries exceeded or other error)
        if not voting_btm_key:
            return

        tag_jobs = TagasaurisJobs.objects.get(urlannotator_job=job)
        tag_jobs.voting_btm_key = voting_btm_key

        # ALWAYS add mediaobject mappings assuming Tagasauris will handle them
        # TODO: possibly check mediaobject status?
        for sample, mediaobject in mediaobjects.items():
            SampleMapping(
                sample=sample,
                external_id=mediaobject['id'],
                crowscourcing_type=SampleMapping.TAGASAURIS,
            ).save()
        log.info(
            'EventBTMSendToHuman: SampleMapping created for BTM %d.' % btm.id
        )

        if voting_btm_hit is not None:
            tag_jobs.voting_btm_hit = voting_btm_hit

        tag_jobs.save()

    else:
        # Creates sample to mediaobject mapping
        mediaobjects = samples_to_mediaobjects([sample, ],
            caption=job.description)

        for sample, mediaobject in mediaobjects.items():
            SampleMapping(
                sample=sample,
                external_id=mediaobject['id'],
                crowscourcing_type=SampleMapping.TAGASAURIS,
            ).save()

        # New objects
        mediaobjects = mediaobjects.values()

        res = update_voting_job(tc, mediaobjects,
            job.tagasaurisjobs.voting_btm_key)

        # If updating was failed - delete created. Why not create them here?
        # Because someone might have completed a HIT in the mean time, and we
        # would lose that info.
        if not res:
            SampleMapping.objects.filter(
                sample__in=imap(lambda x: x.sample, mediaobjects.items())
            ).delete()

        # In case if tagasauris job was created without screenshots earlier.
        if job.tagasaurisjobs.voting_btm_hit is None:
            result = tc.get_job(external_id=job.tagasaurisjobs.voting_btm_key)
            voting_btm_hit = result['hits'][0] if result['hits'] else None
            if voting_btm_hit is not None:
                job.tagasaurisjobs.voting_btm_hit = voting_btm_hit
                job.tagasaurisjobs.save()


@task(ignore_result=True)
def update_job_votes_gathered(sample_id, worker_id):
    sample = Sample.objects.filter(id=sample_id).select_related('job')
    sample[0].job.get_progress_votes(cache=False)

    worker = Worker.objects.get(id=worker_id)
    worker.get_votes_added_count_for_job(sample[0].job, cache=False)

    # Update top workers
    sample[0].job.get_top_workers()


@task(ignore_result=True)
def vote_on_new_sample(sample_id, job_id):
    '''
        Creates a LABEL_YES vote on the brand-new sample by the sample sender.
    '''
    sample = Sample.objects.get(id=sample_id)
    worker = sample.get_source_worker()
    if not worker:
        return

    WorkerQualityVote.objects.new_vote(worker=worker, sample=sample,
        label=LABEL_YES)

FLOW_DEFINITIONS = [
    (r'^EventNewJobInitialization$', initialize_external_jobs, settings.CELERY_LONGSCARCE_QUEUE),
    (r'^EventBTMStarted$', initialize_btm_job, settings.CELERY_LONGSCARCE_QUEUE),
    (r'^EventBTMSendToHuman$', btm_send_to_human, settings.CELERY_LONGSCARCE_QUEUE),
    (r'^EventNewVoteAdded$', update_job_votes_gathered),
    (r'^EventNewSample$', vote_on_new_sample),
    # WIP: DSaS/GAL quality algorithms.
    # (r'^EventGoldSamplesDone$', initialize_quality),
]
