from __future__ import absolute_import

import logging
import re

from celery import task, Task, group
from django.conf import settings

log = logging.getLogger('EventBus')


def flow_modules():
    ''' from django admin code '''
    from django.conf import settings
    from django.utils.importlib import import_module
    from django.utils.module_loading import module_has_submodule

    def tmp(app):
        mod = import_module(app)
        # Attempt to import the app's admin module.
        try:
            return import_module('%s.event_handlers' % app)
        except:
            # Decide whether to bubble up this error. If the app just
            # doesn't have an flow module, we can ignore the error
            # attempting to import it, otherwise we want it to bubble up.
            if module_has_submodule(mod, 'event_handlers'):
                raise
        return None

    return filter(None, (tmp(app) for app in settings.INSTALLED_APPS))


@task(ignore_result=True)
class EventBusSender(Task):
    ''' Matching using regexps
    '''

    def __init__(self):
        self.registered = []
        self.config_yourself()

    def config_yourself(self):
        for module in flow_modules():
            self.update_config(module.FLOW_DEFINITIONS)

    def register(self, event_pattern, fun, queue=settings.CELERY_DEFAULT_QUEUE):
        self.registered.append((re.compile(event_pattern), fun, queue))

    def update_config(self, flow_definition):
        for flow_entry in flow_definition:
            event_pattern = flow_entry[0]
            fun = flow_entry[1]
            queue = settings.CELERY_DEFAULT_QUEUE
            if len(flow_entry) > 3:
                queue = flow_entry[2]
            self.register(event_pattern, fun, queue)

    def run(self, event_name, *args, **kwargs):
        log.debug('Got event: %s(%s, %s)', event_name, args, kwargs)

        dispatched = {}
        for matcher, task_func, queue in self.registered:
            if not matcher.match(event_name):
                continue

            dispatched.setdefault(queue, [])
            dispatched[queue].append(task_func.s(*args, **kwargs))

        if not dispatched:
            log.warning('Event not matched: %s !', event_name)
        else:
            for queue, disp in dispatched.iteritems():
                group(disp).apply_async(queue=queue)
