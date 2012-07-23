import os

from django.test import TestCase

from urlannotator.flow_control import send_event


class TestEventBusSender(TestCase):

    def test_proper_matching(self):

        event_name, file_name, file_content = \
            'TestEvent', "test_file_name", "success"

        send_event(event_name, file_name, file_content)

        # due to eager celery task evaluation this should work
        with open(file_name, 'r') as f:
            self.assertEqual(file_content, f.readline())
        os.remove(file_name)
