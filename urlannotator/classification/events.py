from django.conf import settings

from celery import task, Task, registry

from urlannotator.classification.classifiers import SimpleClassifier
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
        sc = SimpleClassifier(description="test", classes=['Yes'])
        if samples:
            if isinstance(samples, int):
                samples = [samples]
            job = Sample.objects.get(id=samples[0]).job
            all_samples = Sample.objects.filter(job=job)
            if all_samples:
                sc.train(all_samples)
                samples_list = Sample.objects.filter(id__in=samples)
                for sample in samples_list:
                    sc.classify(sample)


add_samples = registry.tasks[ClassifierTrainingManager.name]


@task
def update_classified_sample(sample_id, *args, **kwargs):
    sample = Sample.objects.get(id=sample_id)
    ClassifiedSample.objects.filter(job=sample.job, url=sample.url,
        sample=None).update(sample=sample)
    return None

@task
def classify(*args, **kwargs):
    pass


@task
def update_classifier_stats(*args, **kwargs):
    pass


settings.FLOW_DEFINITIONS += [
    (r'EventNewSample', update_classified_sample),
    (r'EventSamplesValidated', add_samples),
    (r'EventNewClassifySample', add_samples),
    (r'EventTrainClassifier', classify),
    (r'EventClassifierTrained', update_classifier_stats),
]
