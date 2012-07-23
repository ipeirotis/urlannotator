from celery import task

from urlannotator.flow_control import send_event


@task()
def send_validated_samples(samples):
    send_event("EventSamplesValidated", samples)
