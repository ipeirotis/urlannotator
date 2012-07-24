from celery import task, Task, registry

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
            if job.status == 4:
                registry.tasks[ClassifierTrainingManager.name].retry(countdown=30)

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
    training_set = TrainingSet.objects.get(id=set_id)

    # Set project status to active, if initializing
    if training_set.job.status == 4:
        training_set.job.status = 1
        training_set.job.save()

    # FIXME: add actual classifier distinguish
    # classifier = classifier_factory.create_classifier(training_set.job.id)
    pass


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
