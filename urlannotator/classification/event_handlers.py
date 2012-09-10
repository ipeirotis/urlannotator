from multiprocessing.pool import Process

from celery import task, Task, registry
from celery.task import current
from django.conf import settings

from urlannotator.flow_control import send_event
from urlannotator.classification.models import (TrainingSet, ClassifiedSample,
    TrainingSample)
from urlannotator.classification.factories import classifier_factory
from urlannotator.crowdsourcing.models import (SampleMapping, TagasaurisJobs,
    WorkerQualityVote)
from urlannotator.crowdsourcing.tagasauris_helper import (make_tagapi_client,
    create_job, samples_to_mediaobjects)
from urlannotator.crowdsourcing.factories import quality_factory
from urlannotator.main.models import Sample, Job


@task(ignore_result=True)
class ClassifierTrainingManager(Task):
    """ Manage training of classifiers.
    """

    def __init__(self):
        self.samples = []

    def run(self, samples, *args, **kwargs):
        # FIXME: Mock
        # TODO: Make proper classifier management
        if samples:
            if isinstance(samples, int):
                samples = [samples]
            job = Sample.objects.get(id=samples[0]).job

            # If classifier is not trained, retry later
            if not job.is_classifier_trained():
                current.retry(countdown=3 * 60)

            # classifier = classifier_factory.create_classifier(job.id)
            # # train_samples = [train_sample.sample for train_sample in
            # #     TrainingSet.objects.newest_for_job(job).training_samples.all()]
            # # if train_samples:
            # #     classifier.train(train_samples)
            # samples_list = Sample.objects.filter(id__in=samples)
            # for sample in samples_list:
            #     classifier.classify(sample)


add_samples = registry.tasks[ClassifierTrainingManager.name]


@task(ignore_result=True)
class SampleVotingManager(Task):
    """ Task periodically executed for update external voting service with
        newly delivered samples.
    """

    def get_unmapped_samples(self):
        """ New Samples since last update. We should send those to external
            voting service.
        """
        mapped_samples = SampleMapping.objects.select_related('sample').all()
        mapped_samples_ids = set([s.sample.id for s in mapped_samples])
        return Sample.objects.select_related('job').exclude(
            id__in=mapped_samples_ids)

    def get_jobs(self, all_samples):
        """ Auxiliary function for divide samples in job related groups and
            annotate those groups with info if external job should be
            initialized or not. We assume that jobs having already mapped
            samples are initialized, otherwise - not.
        """
        jobs = set([s.job for s in all_samples])

        for job in jobs:
            job_samples = [s for s in all_samples if s.job == job]
            initialized = job.tagasaurisjobs.voting_key is not None
            yield job, job_samples, initialized

    def initialize_job(self, job, new_samples):
        """ Job initialization.
            TODO: Extend in future with other than tagasauris services?
        """
        tc = make_tagapi_client()

        # Creates sample to mediaobject mapping
        mediaobjects = samples_to_mediaobjects(new_samples)

        # Objects to send.
        mo_values = mediaobjects.values()

        # Creating new job with mediaobjects
        voting_key, voting_hit = create_job(tc, job,
            settings.TAGASAURIS_VOTING_WORKFLOW,
            callback=settings.TAGASAURIS_VOTING_CALLBACK % job.id,
            mediaobjects=mo_values)

        tag_jobs = TagasaurisJobs.objects.get(urlannotator_job=job)
        tag_jobs.voting_key = voting_key

        if voting_hit is not None:
            # Update mapping if HIT was generaed. TODO: Not sure if we should
            # check is tagasauris get all our screenshots.
            for sample, mediaobject in mediaobjects.items():
                SampleMapping(
                    sample=sample,
                    external_id=mediaobject['id'],
                    crowscourcing_type=SampleMapping.TAGASAURIS,
                ).save()
            tag_jobs.voting_hit = voting_hit

        tag_jobs.save()

    def update_job(self, job, new_samples):
        """ Updating existing job.
            TODO: Extend in future with other than tagasauris services?
        """
        tc = make_tagapi_client()

        # Creates sample to mediaobject mapping
        mediaobjects = samples_to_mediaobjects(new_samples)

        for sample, mediaobject in mediaobjects.items():
            SampleMapping(
                sample=sample,
                external_id=mediaobject['id'],
                crowscourcing_type=SampleMapping.TAGASAURIS,
            ).save()

        # New objects
        mediaobjects = mediaobjects.values()

        res = tc.mediaobject_send(mediaobjects)
        tc.wait_for_complete(res)

        # We must wait for media objects beeing uploaded before we can attach
        # them to job.
        tc.job_add_media(
            external_ids=[mo['id'] for mo in mediaobjects],
            external_id=job.tagasaurisjobs.voting_key)

        # In case if tagasauris job was created without screenshots earlier.
        if job.tagasaurisjobs.voting_hit is None:
            result = tc.get_job(external_id=job.tagasaurisjobs.voting_key)
            voting_hit = result['hits'][0] if result['hits'] else None
            if voting_hit is not None:
                job.tagasaurisjobs.voting_hit = voting_hit
                job.tagasaurisjobs.save()

    def run(self, *args, **kwargs):
        """ Main task function.
        """
        unmapped_samples = self.get_unmapped_samples()
        jobs = self.get_jobs(unmapped_samples)

        for job, new_samples, initialized in jobs:
            try:
                if initialized:
                    self.update_job(job, new_samples)
                else:
                    self.initialize_job(job, new_samples)
            except Exception:
                # Suppress all exceptions.
                # TODO: Handle possible exceptions properly here. They are
                #       causing bad stuff to happen with worker's RAM
                #       management (10x increase, never garbaged).
                pass


send_for_voting = registry.tasks[SampleVotingManager.name]


@task(ignore_result=True)
class ProcessVotesManager(Task):
    def run(*args, **kwargs):
        active_jobs = Job.objects.get_active()

        for job in active_jobs:
            ts = TrainingSet(job=job)
            ts.save()

            quality_algorithm = quality_factory.create_algorithm(job)

            for sample in job.sample_set.all():
                votes = WorkerQualityVote.objects.filter(sample=sample)
                new_label = quality_algorithm.process_votes(votes)

                if new_label is not None:
                    TrainingSample(
                        set=ts,
                        sample=sample,
                        label=new_label
                    ).save()

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
    send_event(
        "EventClassifierTrained",
        job_id=job.id,
    )


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

    # If we are testing tools, continue with synchronized flow.
    if settings.TOOLS_TESTING:
        train(set_id=set_id)

    else:
        process_execute(target=prepare_func,
            kwargs={'func': train, 'set_id': set_id})

    # Gold samples created (since we are here), classifier created (checked).
    # Job has been fully initialized
    # TODO: Move to job.activate()?
    # send_event('EventNewJobInitializationCompleted')


@task(ignore_result=True)
def classify(sample_id, from_name='', *args, **kwargs):
    """
        Classifies given samples
    """
    class_sample = ClassifiedSample.objects.get(id=sample_id)
    if class_sample.label:
        return

    job = class_sample.job

    # If classifier is not trained, retry later
    if not job.is_classifier_trained():
        current.retry(countdown=min(60 * 2 ** current.request.retries,
            60 * 60 * 24))

    classifier = classifier_factory.create_classifier(job.id)
    label = classifier.classify(class_sample)
    if not label:
        label = 'No'
    class_sample = ClassifiedSample.objects.get(id=sample_id)
    class_sample.label = label
    class_sample.save()
    send_event(
        'EventSampleClassified',
        job_id=job.id,
        class_id=class_sample.id,
        sample_id=class_sample.sample.id,
    )


@task
def update_classifier_stats(job_id, *args, **kwargs):
    pass


FLOW_DEFINITIONS = [
    (r'^EventNewSample$', update_classified_sample),
    (r'^EventSamplesValidated$', add_samples),
    (r'^EventSamplesVoting$', send_for_voting),
    (r'^EventProcessVotes$', process_votes),
    (r'^EventNewClassifySample$', classify),
    # (r'EventTrainClassifier', classify),
    (r'^EventTrainingSetCompleted$', train_on_set),
    (r'^EventClassifierTrained$', update_classifier_stats),
]
