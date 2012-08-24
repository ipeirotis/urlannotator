import os

from django.test import TestCase

from urlannotator.flow_control import send_event
from urlannotator.flow_control.test import FlowControlMixin


class TestEventBusSender(TestCase):

    def test_proper_matching(self):
        event_name, file_name, file_content = \
            'TestEvent', "test_file_name", "success"

        send_event(event_name,
            fname=file_name,
            content=file_content)

        # due to eager celery task evaluation this should work
        with open(file_name, 'r') as f:
            self.assertEqual(file_content, f.readline())
        os.remove(file_name)


class TestEvenFlowSuppressing(FlowControlMixin, TestCase):

    def suppress_events(self):
        return ['TestEvent', ]

    def test_suppression(self):
        event_name, file_name, file_content = \
            'TestEvent', "test_file_name", "success"

        send_event(event_name,
            fname=file_name,
            content=file_content)

        self.assertFalse(os.path.isfile(file_name))


class TestEvenFlowAltering(FlowControlMixin, TestCase):

    def flow_definition(self):
        from urlannotator.flow_control.event_handlers import test_task_2
        return [
            (r'^TestEvent$', test_task_2),
        ]

    def test_altering(self):
        event_name, file_name, file_content = \
            'TestEvent', "test_file_name", "success"

        send_event(event_name,
            fname=file_name,
            content=file_content)

        with open(file_name, 'r') as f:
            self.assertEqual(file_content[::-1], f.readline())
        os.remove(file_name)
