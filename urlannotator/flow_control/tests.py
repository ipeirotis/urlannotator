import os

from django.utils import unittest

from urlannotator.flow_control import event_bus


class TestEventBusSender(unittest.TestCase):

    def test_proper_matching(self):

        event_name, file_name, file_content = \
            'TestEvent', "test_file_name", "success"
        event_bus.delay(event_name, file_name, file_content)
        # due to eager celery task evaluation this should work
        with open(file_name, 'r') as f:
            self.assertEqual(file_content, f.readline())
        os.remove(file_name)


