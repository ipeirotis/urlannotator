from celery import registry
from django.conf import settings


class EventSystemException(Exception):
    pass


def send_event(event_name, *args, **kwargs):
    from event_system import EventBusSender
    if args:
        raise EventSystemException("Illegal use of send_event. "
            "Only kwargs allowed.")

    return registry.tasks[EventBusSender.name].apply_async(
        args=[event_name], kwargs=kwargs,
        queue=settings.CELERY_REALTIME_QUEUE
    )
