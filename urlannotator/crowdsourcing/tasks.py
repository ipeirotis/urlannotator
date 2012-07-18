from celery import task

from urlannotator.flow_control.event_system import event_bus


@task()
def send_validated_samples(samples):
    event_bus.delay("EventSamplesValidated", samples)
