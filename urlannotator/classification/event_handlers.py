from celery import task, Task, registry

from urlannotator.flow_control import send_event
from urlannotator.classification.models import TrainingSet
from urlannotator.classification.factories import classifier_factory
from urlannotator.main.models import Sample, ClassifiedSample


@task()
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
            if job.is_classifier_trained():
                registry.tasks[ClassifierTrainingManager.name].retry(
                    countdown=30)

            classifier = classifier_factory.create_classifier(job.id)
            train_samples = [train_sample.sample for train_sample in
                TrainingSet.objects.newest_for_job(job).training_samples.all()]
            if train_samples:
                classifier.train(train_samples)
                samples_list = Sample.objects.filter(id__in=samples)
                for sample in samples_list:
                    classifier.classify(sample)


add_samples = registry.tasks[ClassifierTrainingManager.name]


@task
def update_classified_sample(sample_id, *args, **kwargs):
    """
        Monitors sample creation and updates classify requests with this sample
        on match.
    """
    sample = Sample.objects.get(id=sample_id)
    ClassifiedSample.objects.filter(job=sample.job, url=sample.url,
        sample=None).update(sample=sample)
    return None


@task
def train_on_set(set_id):
    """
        Trains classifier on newly created training set
    """
    training_set = TrainingSet.objects.get(id=set_id)
    job = training_set.job

    # If classifier hasn't been created, retry later
    if not job.is_classifier_created():
        train_on_set.retry(countdown=30)

    classifier = classifier_factory.create_classifier(job.id)

    samples = (training_sample.sample
        for training_sample in training_set.training_samples.all())
    classifier.train(samples)
    job.set_classifier_trained()

    # Gold samples created (since we are here), classifier created (checked).
    # Job has been fully initialized
    # TODO: Move to job.activate()?
    send_event('EventNewJobInitializationCompleted')


@task
def classify(*args, **kwargs):
    """
        Classifies given samples
    """
    pass


@task
def update_classifier_stats(*args, **kwargs):
    pass


FLOW_DEFINITIONS = [
    (r'EventNewSample', update_classified_sample),
    (r'EventSamplesValidated', add_samples),
    (r'EventNewClassifySample', classify),
    # (r'EventTrainClassifier', classify),
    (r'EventTrainingSetCompleted', train_on_set),
    (r'EventClassifierTrained', update_classifier_stats),
]
