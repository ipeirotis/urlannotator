import os

from django.test import TestCase

from urlannotator.flow_control import event_bus


class TestEventBusSender(TestCase):

    def test_proper_matching(self):

        event_name, file_name, file_content = \
            'TestEvent', "test_file_name", "success"

        result = event_bus.delay(event_name, file_name, file_content)
        group_result = result.get()
        group_result.get()  # Now dispatched events are 100% finished.

        with open(file_name, 'r') as f:
            self.assertEqual(file_content, f.readline())
        os.remove(file_name)
