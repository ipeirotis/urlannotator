from __future__ import absolute_import

import logging

from celery import Task

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
            return import_module('%s.flow' % app)
        except:
            # Decide whether to bubble up this error. If the app just
            # doesn't have an flow module, we can ignore the error
            # attempting to import it, otherwise we want it to bubble up.
            if module_has_submodule(mod, 'flow'):
                raise
        return None

    return filter(None, (tmp(app) for app in settings.INSTALLED_APPS))


class EventBusSender(Task):
    ''' Easy version - no matching on event names - just equality
    '''

    def __init__(self):
        self.registered = {}
        self.config_yourself()

    def config_yourself(self):
        for module in flow_modules():
            self.update_config(module.FLOW_DEFINITIONS)

    def register(self, event_pattern, fun):
        print "registered: ", event_pattern
        self.registered.setdefault(event_pattern, []).append(fun)

    def update_config(self, flow_definition):
        for event_pattern, fun in flow_definition:
            self.register(event_pattern, fun)

    def run(self, event_name, *args, **kwargs):
        print "RUN"
        log.debug('Got event: %s(%s, %s)', event_name, args, kwargs)
        if event_name not in self.registered:
            log.warning('Event not catched: %s !', event_name)
        else:
            self.run_tasks(self.registered[event_name], *args, **kwargs)

    def run_tasks(self, tasks, *args, **kwargs):
        for task in tasks:
            task.delay(*args, **kwargs)
        # TODO this should be called with some error handling
