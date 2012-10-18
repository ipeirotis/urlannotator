import os

from django.test import TestCase
from django.contrib.auth.models import User

from urlannotator.flow_control import send_event
from urlannotator.flow_control.test import (FlowControlMixin,
    ToolsMockedMixin, ToolsMocked)
from urlannotator.flow_control.event_handlers import test_task_2
from urlannotator.main.models import Sample, Job, LABEL_YES


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


class TestEventFlowSuppressing(FlowControlMixin, TestCase):

    suppress_events = ['TestEvent', ]

    def test_suppression(self):
        event_name, file_name, file_content = \
            'TestEvent', "test_file_name", "success"

        send_event(event_name,
            fname=file_name,
            content=file_content)

        self.assertFalse(os.path.isfile(file_name))


class TestEventFlowAltering(FlowControlMixin, TestCase):

    flow_definition = [
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


class TestToolsMocking(ToolsMockedMixin, TestCase):
    def testBasicMock(self):
        u = User.objects.create_user(username='test', password='test')
        j = Job.objects.create_active(
            account=u.get_profile(),
            gold_samples=[{'url': 'http://google.com', 'label': LABEL_YES}],
        )

        s = Sample.objects.get(job=j, url='http://google.com')
        self.assertEqual(s.screenshot, '')
        self.assertEqual(s.text, '')

    def testContextMock(self):
        def test_mock():
            raise Exception

        mock_target = ('urlannotator.flow_control.tests.Sample.objects'
                       '.create_by_owner')

        with ToolsMocked(mocks=[(mock_target, test_mock), ]):
            with self.assertRaises(Exception):
                Sample.objects.create_by_owner()
