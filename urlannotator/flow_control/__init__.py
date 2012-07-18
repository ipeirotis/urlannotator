from celery import registry


def get_event_bus():
    from event_system import EventBusSender
    return registry.tasks[EventBusSender.name]
