from celery import registry


def send_event(event_name, *args, **kwargs):
    from event_system import EventBusSender
    return registry.tasks[EventBusSender.name].delay(event_name, *args,
        **kwargs)
