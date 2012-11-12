from multiprocessing.pool import Process

from celery import task, Task, registry
from celery.task import current
from django.conf import settings
from itertools import imap

from urlannotator.flow_control import send_event
from urlannotator.classification.models import (TrainingSet, ClassifiedSample,
    TrainingSample)
from urlannotator.classification.factories import classifier_factory
from urlannotator.crowdsourcing.models import (SampleMapping, TagasaurisJobs,
    BeatTheMachineSample)
from urlannotator.crowdsourcing.tagasauris_helper import (make_tagapi_client,
    create_voting, samples_to_mediaobjects, update_voting_job, get_hit)
from urlannotator.crowdsourcing.factories import quality_factory
from urlannotator.crowdsourcing.job_handlers import get_job_handler
from urlannotator.main.models import (Sample, Job, LABEL_BROKEN,
    JOB_STATUS_ACTIVE)
from urlannotator.tools.synchronization import singleton

import logging
log = logging.getLogger(__name__)

# Max amount of samples to update. To avoid a single job blocking whole service
# while uploading loads of medias.
VOTING_MAX_SAMPLES = 100


@task(ignore_result=True)
class SampleVotingManager(Task):
    """ Task periodically executed for update external voting service with
        newly delivered samples.
    """

    def get_unmapped_samples(self):
        """ New Samples since last update. We should send those to external
            voting service. Samples are sorted by job, so we can use an
            iterator and save loads of memory.
        """
        samples = Sample.objects.select_related('job').filter(
            vote_sample=True, samplemapping=None,
            job__status=JOB_STATUS_ACTIVE,
            job__tagasaurisjobs__isnull=False).exclude(screenshot='')
        return samples.order_by('job')[:VOTING_MAX_SAMPLES].iterator()

    def get_jobs(self, all_samples):
        """ Auxiliary function for divide samples in job related groups and
            annotate those groups with info if external job should be
            initialized or not. We assume that jobs having already mapped
            samples are initialized, otherwise - not.
        """
        job = None
        tag_job = False
        samples = []
        for sample in all_samples:
            if job != sample.job:
                if samples:
                    yield job, samples, tag_job
                    samples = []
                    tag_job = False

                job = sample.job
                try:
                    tag_job = job.tagasaurisjobs.voting_key is not None
                except TagasaurisJobs.DoesNotExist:
                    log.warning("Spotted job %d without tagasauris link." % job.id)
                    tag_job = False

            if not job.is_active():
                continue

            samples.append(sample)

        # The last job's samples
        if samples:
            yield job, samples, tag_job

    def initialize_job(self, tc, job, new_samples):
        """ Job initialization.
        """

        # Creates sample to mediaobject mapping
        mediaobjects = samples_to_mediaobjects(new_samples,
            caption=job.description)

        # Creating new job  with mediaobjects
        log.info(
            'SampleVotingManager: Creating voting job for job %d.' % job.id
        )

        handler = get_job_handler(job)
        handler.init_voting(tc, job, mediaobjects)

    def update_job(self, tc, job, new_samples):
        """ Updating existing job.
        """
        # Creates sample to mediaobject mapping
        mediaobjects = samples_to_mediaobjects(new_samples,
            caption=job.description)
        log.info(
            'SampleVotingManager: Mapped mediaobjects dict for job %d. '
            'Creating SampleMappings.' % job.id
        )

        handler = get_job_handler(job)
        handler.update_voting(tc, job, mediaobjects)

    @singleton(name='voting-manager')
    def run(self, *args, **kwargs):
        """ Main task function.
        """
        try:
            unmapped_samples = self.get_unmapped_samples()
            jobs = self.get_jobs(unmapped_samples)
            tc = make_tagapi_client()

            log.info('SampleVotingManager: Gathered samples and jobs.')
            for job, new_samples, initialized in jobs:
                try:
                    if initialized:
                        self.update_job(tc, job, new_samples)

                    else:
                        self.initialize_job(tc, job, new_samples)
                except Exception, e:
                    log.warning(
                        'SampleVotingManager: Error in job %d: %s.' % (job.id, e)
                    )
                    continue
        except Exception, e:
            log.critical(
                'SampleVotingManager: exception while all jobs: %s.' % e
            )


send_for_voting = registry.tasks[SampleVotingManager.name]


@task(ignore_result=True)
class SampleGatheringMonitor(Task):
    """
        Checks jobs' sample gathering job for HIT changes.
    """
    def run(*args, **kwargs):
        jobs = Job.objects.select_related('tagasaurisjobs').filter(
            status=JOB_STATUS_ACTIVE,
            tagasaurisjobs__isnull=False,
            tagasaurisjobs__sample_gathering_hit='').iterator()
        client = make_tagapi_client()

        for job in jobs:
            old_hit = job.tagasaurisjobs.sample_gathering_hit
            new_hit = get_hit(client, job.tagasaurisjobs.sample_gathering_key)
            if old_hit != new_hit:
                send_event(
                    'EventSampleGathertingHITChanged',
                    job_id=job.id,
                    old_hit=old_hit,
                    new_hit=new_hit,
                )
            TagasaurisJobs.objects.filter(urlannotator_job=job).update(
                sample_gathering_hit=new_hit
            )


@task(ignore_result=True)
class ProcessVotesManager(Task):
    @singleton(name='process-votes')
    def run(*args, **kwargs):
        active_jobs = Job.objects.get_active()

        for job in active_jobs:
            if not job.has_new_votes():
                continue

            quality_algorithm = quality_factory.create_algorithm(job)
            decisions = quality_algorithm.extract_decisions()
            if decisions:
                log.info(
                    'ProcessVotesManager: Creating training set for job %d.' % job.id
                )

                ts = TrainingSet.objects.create(job=job)
                for sample_id, label in decisions:
                    if label == LABEL_BROKEN:
                        log.info(
                            'ProcessVotesManager: Omitted broken label of sample %d.' % sample_id
                        )
                        continue

                    sample = Sample.objects.get(id=sample_id)
                    if not sample.training:
                        continue  # Skipping (BTM non trainable sample)

                    TrainingSample.objects.create(
                        set=ts,
                        sample=sample,
                        label=label,
                    )

                for sample in Sample.objects.filter(job=job).iterator():
                    if sample.is_gold_sample():
                        ts_sample, created = TrainingSample.objects.get_or_create(
                            set=ts,
                            sample=sample,
                        )
                        if not created:
                            log.info(
                                'ProcessVotesManager: Overriden gold sample %d.' % sample.id
                            )
                        ts_sample.label = sample.goldsample.label
                        ts_sample.save()

                send_event(
                    'EventTrainingSetCompleted',
                    set_id=ts.id,
                    job_id=job.id,
                )

            decisions = quality_algorithm.extract_btm_decisions()
            if decisions:
                log.info(
                    'ProcessVotesManager: Processing btm decisions %d.' % job.id
                )

                for sample_id, label in decisions:
                    if label == LABEL_BROKEN:
                        log.info(
                            'ProcessVotesManager: Omitted broken label of btm sample %d.' % sample_id
                        )
                        continue

                    btms = BeatTheMachineSample.objects.get(
                        sample__id=sample_id)
                    btms.recalculate_human(label)


process_votes = registry.tasks[ProcessVotesManager.name]


@task(ignore_result=True)
def update_classified_sample(sample_id, *args, **kwargs):
    """
        Monitors sample creation and updates classify requests with this sample
        on match.
    """
    sample = Sample.objects.get(id=sample_id)

    ClassifiedSample.objects.filter(job=sample.job, url=sample.url,
        sample=None).update(sample=sample)
    classified = ClassifiedSample.objects.filter(
        job=sample.job,
        url=sample.url,
        sample=sample,
        label=''
    )
    for class_sample in classified:
        send_event("EventNewClassifySample",
            sample_id=class_sample.id,
            from_name='update_classified')


@task(ignore_result=True)
def update_btm_sample(sample_id, *args, **kwargs):
    """
        Monitors sample creation and updates classify requests with this sample
        on match.
    """
    sample = Sample.objects.get(id=sample_id)
    BeatTheMachineSample.objects.filter(job=sample.job, url=sample.url,
        sample=None).update(sample=sample)
    btms = BeatTheMachineSample.objects.filter(
        job=sample.job,
        url=sample.url,
        sample=sample,
        label=''
    )
    for btm_sample in btms:
        send_event("EventNewClassifyBTMSample",
            sample_id=btm_sample.id,
            from_name='update_classified')


def process_execute(*args, **kwargs):
    """
        Executes func from keyword arguments with values from them.
        Args and kwargs are directly passed to multiprocessing.Process.
    """
    from django.db import transaction
    # Commit current transaction so that new process will have up-to-date DB.
    if transaction.is_dirty():
        transaction.commit()

    proc = Process(*args, **kwargs)
    proc.start()


def prepare_func(func, *args, **kwargs):
    """
        Closes django connection before executing the function.
        Used in subprocessing to enforce fresh connection.
    """
    from django.db import connection
    connection.close()

    return func(*args, **kwargs)


def train(set_id):
    training_set = TrainingSet.objects.get(id=set_id)
    job = training_set.job

    classifier = classifier_factory.create_classifier(job.id)

    samples = (training_sample
        for training_sample in training_set.training_samples.all())

    classifier.train(samples, set_id=set_id)

    job = Job.objects.get(id=job.id)
    if job.is_classifier_trained():
        send_event(
            "EventClassifierTrained",
            job_id=job.id,
        )

        # Reclassify samples using new classifier
        # job.reclassify_samples()


@task(ignore_result=True)
def train_on_set(set_id, *args, **kwargs):
    """
        Trains classifier on newly created training set
    """
    training_set = TrainingSet.objects.get(id=set_id)
    job = training_set.job

    # If classifier hasn't been created, retry later.
    if not job.is_classifier_created():
        train_on_set.retry(countdown=30)

    process_execute(target=prepare_func,
        kwargs={'func': train, 'set_id': set_id})


@task(ignore_result=True)
def classify(sample_id, from_name='', *args, **kwargs):
    """
        Classifies given samples
    """
    class_sample = ClassifiedSample.objects.get(id=sample_id)
    if class_sample.label:
        return

    job = class_sample.job

    # If classifier is not trained, return - it will be reclassified if
    # the classifier finishes training
    if not job.is_classifier_trained():
        return

    classifier = classifier_factory.create_classifier(job.id)
    label = classifier.classify(class_sample)
    if label is None:
        # Something went wrong
        log.warning(
            '[Classification] Got None label for sample %d. Retrying.' % class_sample.id
        )
        current.retry(
            countdown=min(60 * 2 ** (current.request.retries % 6), 60 * 60 * 1),
            max_retries=None,
        )
    ClassifiedSample.objects.filter(id=sample_id).update(label=label)

    send_event(
        'EventSampleClassified',
        job_id=job.id,
        class_id=class_sample.id,
        sample_id=class_sample.sample.id,
    )


@task(ignore_result=True)
def classify_btm(sample_id, from_name='', *args, **kwargs):
    """
        Classifies given samples
    """
    log.info(
        '[BTMClassification] Got sample %d for classification.' % sample_id
    )
    btm_sample = BeatTheMachineSample.objects.get(id=sample_id)
    if btm_sample.label:
        return

    job = btm_sample.job

    # If classifier is not trained, retry later
    if not job.is_classifier_trained():
        current.retry(countdown=min(60 * 2 ** current.request.retries,
            60 * 60 * 24))

    classifier = classifier_factory.create_classifier(job.id)
    label = classifier.classify(btm_sample)
    if label is None:
        # Something went wrong
        log.warning(
            '[BTMClassification] Got None label for sample %d. Retrying.'
                % btm_sample.id
        )
        current.retry(countdown=min(60 * 2 ** current.request.retries,
            60 * 60 * 24))

    BeatTheMachineSample.objects.filter(id=sample_id).update(label=label)
    btm_sample.updateBTMStatus()

    send_event(
        'EventSampleBTM',
        job_id=job.id,
        btm_id=btm_sample.id,
        sample_id=btm_sample.sample.id,
    )


@task
def update_classifier_stats(job_id, *args, **kwargs):
    pass


FLOW_DEFINITIONS = [
    (r'^EventNewSample$', update_classified_sample),
    (r'^EventNewBTMSample$', update_btm_sample),
    (r'^EventSamplesVoting$', send_for_voting, settings.CELERY_LONGSCARCE_QUEUE),
    (r'^EventProcessVotes$', process_votes, settings.CELERY_LONGSCARCE_QUEUE),
    (r'^EventNewClassifySample$', classify),
    (r'^EventNewClassifyBTMSample$', classify_btm),
    (r'^EventTrainingSetCompleted$', train_on_set, settings.CELERY_LONGSCARCE_QUEUE),
    (r'^EventClassifierTrained$', update_classifier_stats),
]
