from itertools import ifilter, imap
from multiprocessing.pool import Process

from celery import task, Task, registry
from celery.task import current
from django.conf import settings
from django.db.models import Count

from urlannotator.flow_control import send_event
from urlannotator.classification.models import (TrainingSet, ClassifiedSample,
    TrainingSample)
from urlannotator.classification.factories import classifier_factory
from urlannotator.crowdsourcing.models import (TagasaurisJobs,
    BeatTheMachineSample)
from urlannotator.crowdsourcing.tagasauris_helper import (make_tagapi_client,
    get_hit)
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
                    handler = get_job_handler(job)
                    if initialized:
                        handler.update_voting(tc=tc, samples=new_samples)
                    else:
                        handler.init_voting(tc=tc, samples=new_samples)
                except Exception, e:
                    log.exception(
                        'SampleVotingManager: Error in job %d: %s.' % (job.id, e)
                    )
                    continue
        except Exception, e:
            log.exception(
                'SampleVotingManager: exception while all jobs: %s.' % e
            )


send_for_voting = registry.tasks[SampleVotingManager.name]


class HITMonitor(object):
    def run(self, *args, **kwargs):
        kw = {
            'tagasaurisjobs__%s' % self.hit_name: None,
            'tagasaurisjobs__%s__isnull' % self.key_name: False,
        }
        jobs = Job.objects.select_related('tagasaurisjobs').filter(
            status=JOB_STATUS_ACTIVE,
            tagasaurisjobs__isnull=False, **kw).iterator()
        client = make_tagapi_client()

        for job in jobs:
            old_hit = getattr(job.tagasaurisjobs, self.hit_name)
            new_hit = get_hit(client,
                getattr(job.tagasaurisjobs, self.key_name), job.get_hit_type())

            if not new_hit or old_hit == new_hit:
                continue

            kw = {self.hit_name: new_hit}
            TagasaurisJobs.objects.filter(urlannotator_job=job).update(
                **kw
            )
            send_event(
                self.event_name,
                job_id=job.id,
                old_hit=old_hit,
                new_hit=new_hit,
            )


@task(ignore_result=True)
class SampleGatheringHITMonitor(HITMonitor, Task):
    """
        Checks jobs' sample gathering job for HIT changes.
    """
    hit_name = 'sample_gathering_hit'
    key_name = 'sample_gathering_key'
    event_name = 'EventSampleGatheringHITChanged'

    @singleton(name='samplegather-hit')
    def run(self, *args, **kwargs):
        super(self.__class__, self).run(*args, **kwargs)


@task(ignore_result=True)
def sample_gathering_hit_change(job_id, old_hit, new_hit, **kwargs):
    job = Job.objects.get(id=job_id)
    handler = get_job_handler(job)
    handler.sample_gathering_hit_changed(old=old_hit, new=new_hit)


@task(ignore_result=True)
class VotingHITMonitor(HITMonitor, Task):
    """
        Checks jobs' sample gathering job for HIT changes.
    """
    hit_name = 'voting_hit'
    key_name = 'voting_key'
    event_name = 'EventVotingHITChanged'

    @singleton(name='voting-hit')
    def run(self, *args, **kwargs):
        super(self.__class__, self).run(*args, **kwargs)


@task(ignore_result=True)
def voting_hit_change(job_id, old_hit, new_hit, **kwargs):
    job = Job.objects.get(id=job_id)
    handler = get_job_handler(job)
    handler.voting_hit_changed(old=old_hit, new=new_hit)


@task(ignore_result=True)
class BTMGatheringHITMonitor(HITMonitor, Task):
    """
        Checks jobs' sample gathering job for HIT changes.
    """
    hit_name = 'beatthemachine_hit'
    key_name = 'beatthemachine_key'
    event_name = 'EventBTMGatheringHITChanged'

    @singleton(name='btm-gathering-hit')
    def run(self, *args, **kwargs):
        super(self.__class__, self).run(*args, **kwargs)


@task(ignore_result=True)
def btm_gathering_hit_change(job_id, old_hit, new_hit, **kwargs):
    job = Job.objects.get(id=job_id)
    handler = get_job_handler(job)
    handler.voting_hit_changed(old=old_hit, new=new_hit)


@task(ignore_result=True)
class BTMVotingHITMonitor(HITMonitor, Task):
    """
        Checks jobs' sample gathering job for HIT changes.
    """
    hit_name = 'voting_btm_hit'
    key_name = 'voting_btm_key'
    event_name = 'EventBTMVotingHITChanged'

    @singleton(name='voting-btm-hit')
    def run(self, *args, **kwargs):
        super(self.__class__, self).run(*args, **kwargs)


@task(ignore_result=True)
def btm_voting_hit_change(job_id, old_hit, new_hit, **kwargs):
    job = Job.objects.get(id=job_id)
    handler = get_job_handler(job)
    handler.btm_voting_hit_changed(old=old_hit, new=new_hit)


@task(ignore_result=True)
class ProcessVotesManager(Task):
    @singleton(name='process-votes')
    def run(*args, **kwargs):
        active_jobs = Job.objects.\
            filter(sample__workerqualityvote__is_new=True).\
            annotate(Count('sample__workerqualityvote__is_new'))

        for job in active_jobs:
            quality_algorithm = quality_factory.create_algorithm(job)
            decisions = quality_algorithm.extract_decisions()
            ts = TrainingSet.objects.create(job=job)
            can_train = False
            if decisions:
                log.info(
                    'ProcessVotesManager: Creating training set for job %d.' % job.id
                )

                dict_decisions = dict(decisions)
                samples = Sample.objects.filter(id__in=imap(lambda x: x[0],
                    ifilter(
                        lambda x: x[1] != LABEL_BROKEN, decisions
                    )), training=True).defer('id')

                for sample in samples:
                    TrainingSample.objects.create(
                        set=ts,
                        sample=sample,
                        label=dict_decisions[sample.id],
                    )
                    can_train = True

                for sample in Sample.objects.\
                        filter(job=job, goldsample__isnull=False).\
                        select_related('goldsample').iterator():
                    ts_sample, created = TrainingSample.objects.get_or_create(
                        set=ts,
                        sample=sample,
                    )
                    can_train = True

                    if not created:
                        log.info(
                            'ProcessVotesManager: Overridden gold sample %d.' % sample.id
                        )
                    ts_sample.label = sample.goldsample.label
                    ts_sample.save()

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

                    if btms.sample.training:
                        can_train = True
                        TrainingSample.objects.create(
                            set=ts,
                            sample=btms.sample,
                            label=label,
                        )

            if can_train:
                send_event(
                    'EventTrainingSetCompleted',
                    set_id=ts.id,
                    job_id=job.id,
                )
            else:
                ts.delete()

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
    (r'^EventSampleGatheringHITChanged$', sample_gathering_hit_change, settings.CELERY_LONGSCARCE_QUEUE),
    (r'^EventVotingHITChanged$', voting_hit_change, settings.CELERY_LONGSCARCE_QUEUE),
    (r'^EventBTMGatheringHITChanged$', btm_gathering_hit_change, settings.CELERY_LONGSCARCE_QUEUE),
    (r'^EventBTMVotingHITChanged$', btm_voting_hit_change, settings.CELERY_LONGSCARCE_QUEUE),
]
