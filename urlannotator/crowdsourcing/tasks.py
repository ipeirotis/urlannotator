from celery import task

from urlannotator.flow_control import send_event


@task(ignore_result=True)
def send_validated_samples(samples):
    send_event("EventSamplesValidated", samples=samples)
