from celery import registry


class EventSystemException(Exception):
    pass


def send_event(event_name, *args, **kwargs):
    from event_system import EventBusSender
    if args:
        raise EventSystemException("Illegal use of send_event. "
            "Only kwargs allowed.")

    return registry.tasks[EventBusSender.name].delay(event_name, *args,
        **kwargs)
