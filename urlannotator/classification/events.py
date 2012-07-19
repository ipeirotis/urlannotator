from django.conf import settings

from celery import task, Task, registry


@task()
class ClassifierTrainingManager(Task):
    """ Manage training of classifiers.
    """

    def __init__(self):
        self.samples = []

    def run(self, samples, *args, **kwargs):
        pass

add_samples = registry.tasks[ClassifierTrainingManager.name]


@task
def classifiy(*args, **kwargs):
    pass


@task
def update_classifier_stats(*args, **kwargs):
    pass


settings.FLOW_DEFINITIONS += [
    (r'EventSamplesValidated', add_samples),
    (r'EventTrainClassifier', classifiy),
    (r'EventClassifierTrained', update_classifier_stats),
]
