from __future__ import absolute_import

import logging
import re

from django.conf import settings

from celery import task, Task, registry, group

log = logging.getLogger('EventBus')


@task()
class EventBusSender(Task):
    ''' Matching using regexps
    '''

    def __init__(self):
        self.registered = None

    def update_config(self):
        for event_pattern, fun in settings.FLOW_DEFINITIONS:
            self.register(event_pattern, fun)

    def register(self, event_pattern, fun):
        self.registered.append((re.compile(event_pattern), fun))

    def run(self, event_name, *args, **kwargs):
        log.debug('Got event: %s(%s, %s)', event_name, args, kwargs)

        if self.registered is None:
            self.registered = []
            self.update_config()

        matched = False
        dispatched = []
        for matcher, task_func in self.registered:
            if matcher.match(event_name):
                matched = True
                dispatched.append(task_func.s(*args, **kwargs))

        if not matched:
            log.warning('Event not matched: %s !', event_name)

        return group(dispatched).apply_async()

event_bus = registry.tasks[EventBusSender.name]
