from django.utils import unittest

from urlannotator.flow_control.event_system import EventBusSender


class TestEventBusSender(unittest.TestCase):

    def setUp(self):
        self.ebs = EventBusSender()

    def test_all(self):
        event_name = 'TestEvent'
        r = self.ebs.delay(event_name, 12, 4)  # , key='keyyy')
#        self.assertEqual(16, r.get())
