import re
import mock
from itertools import chain
from contextlib import contextmanager
from celery import task, registry


class FlowControlMixin(object):
    """ Add flow_definition and/or suppress_events for event flow edition.
        Alternative for flow_definition property is get_flow_definition method.
    """

    def _new_registered(self):
        flow = getattr(self, 'flow_definition', self.get_flow_definition())
        suppress_events = getattr(self, 'suppress_events', [])

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

        res = super(FlowControlMixin, self)._pre_setup()

        # Ensures that all celery tasks are loaded and registered in celery and
        # urlannotator event system.
        from event_system import EventBusSender

        # Registered task object.
        bus_sender = registry.tasks[EventBusSender.name]

        # Memorizing original configuration.
        self._original_registered = bus_sender.registered

        # Switching configuration for new one.
        bus_sender.registered = list(self._new_registered())

        return res

    def _post_teardown(self):
        """ Restores original flow definitions.
        """

        from event_system import EventBusSender
        bus_sender = registry.tasks[EventBusSender.name]
        bus_sender.registered = self._original_registered

        super(FlowControlMixin, self)._post_teardown()

    def get_flow_definition(self):
        """ This can be overriden with custom flow definitions.
            Returns list of tuples (pattern, task).
        """
        return self._original_registered


@task()
def mocked_task(*args, **kwargs):
    """
        Empty mocked celery task.
    """
    pass

hardcoded_mocks = [
    ('urlannotator.main.factories.web_content_extraction', mocked_task),
    ('urlannotator.main.factories.web_screenshot_extraction', mocked_task),
]


def apply_patches(mocks=[]):
    """
        Applies passed list of mocks and hardcoded list of always-patched
        objects.

        :rtype: List of patchers.
    """
    mocks = chain(mocks, hardcoded_mocks)
    return map(lambda x: mock.patch(
        target=x[0],
        new=x[1],
    ), mocks)


@contextmanager
def ToolsMocked(mocks=[]):
    """
        Context manager to mock tools and any additional objects.

        :param mocks: Optional list of 2-tuples (target, mock). For each tuple,
                      `target` will be imported and mocked with `mock`.
                      Be careful when specifying `target` and refer to
                      mock.patch of mock module for additional information.
    """
    patchers = apply_patches(mocks)
    map(lambda x: x.start(), patchers)
    yield
    map(lambda x: x.stop(), patchers)


class ToolsMockedMixin(object):
    """
        Mixin to be used with TestCase that mocks web extraction tools.
        Use attribute `mocks` to hold a list of 2-tuples (`target`, `mock`)
        for custom mocking. See mock.patch of mock module for reference.
    """
    def _pre_setup(self):
        self.patchers = apply_patches(getattr(self, 'mocks', []))
        map(lambda x: x.start(), self.patchers)
        super(ToolsMockedMixin, self)._pre_setup()

    def _post_teardown(self):
        super(ToolsMockedMixin, self)._post_teardown()
        map(lambda x: x.stop(), self.patchers)
