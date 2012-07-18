from celery import task


@task
def update_classifier_stats(classifier_data):
    pass


FLOW_DEFINITIONS = [
    (r'EventClassifierTrained', update_classifier_stats),
]
