import re

from celery import registry


class FlowControlMixin(object):

    def _new_registered(self):
        flow = self.flow_definition()
        suppress_events = self.suppress_events()

        for matcher, task_func in flow:
            if type(matcher) is str:
                matcher = re.compile(matcher)
            # If match any suppressed event - skip it.
            # Event is suppressed when it doesn't start any task.
            if not any([matcher.match(event) for event in suppress_events]):
                yield (matcher, task_func)

    def _pre_setup(self):
        """ Alters flow definitions. Since we are using CeleryTestSuiteRunner
            we don't need to care of workers not beeing restarted.
        """

        # Ensures that all celery tasks are loaded and registered in celery and
        # urlannotator event system.
        from event_system import EventBusSender

        # Registered task object.
        bus_sender = registry.tasks[EventBusSender.name]

        # Memorizing original configuration.
        self._original_registered = bus_sender.registered

        # Switching configuration for new one.
        bus_sender.registered = list(self._new_registered())

        return super(FlowControlMixin, self)._pre_setup()

    def _post_teardown(self):
        """ Restores original flow definitions.
        """

        from event_system import EventBusSender
        bus_sender = registry.tasks[EventBusSender.name]
        bus_sender.registered = self._original_registered

        super(FlowControlMixin, self)._post_teardown()

    def flow_definition(self):
        """ This can be overriden with custom flow definitions.
            Returns list of tuples (pattern, task).
        """
        return self._original_registered

    def suppress_events(self):
        """ Override this function with list of events to suppress.
        """
        return []
