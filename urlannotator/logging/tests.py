from django.test import TestCase
from django.contrib.auth.models import User

from urlannotator.main.models import Job
from urlannotator.logging.models import LogEntry
from urlannotator.logging.settings import (LOG_TYPE_NEW_SAMPLE_DONE,
    LOG_TYPE_JOB_INIT_START)


class LoggingTest(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')

        self.job = Job.objects.create_active(
            account=self.u.get_profile(),
            gold_samples=[{'url': '10clouds.com', 'label': 'Yes'}])

    def test_visibility(self):
        # No user-visible logs shouldve been added.
        logs = LogEntry.objects.unread_for_user(self.u)
        self.assertFalse(logs)

        # What about recent alerts?
        logs = LogEntry.objects.recent_for_job(self.job)
        self.assertFalse(logs)

        # Lets add a user-visible alert - new sample done.
        params = {
            'sample_id': 0,
            'sample_url': 'test',
            'sample_screenshot': 'test',
        }
        LogEntry.objects.log(
            log_type=LOG_TYPE_NEW_SAMPLE_DONE,
            job=self.job,
            params=params,
        )

        # Now there should be a user-visible, unread log.
        logs = LogEntry.objects.unread_for_user(self.u)
        self.assertTrue(logs)

        # Lets see if it has been flagged as read.
        logs = LogEntry.objects.unread_for_user(self.u)
        self.assertFalse(logs)

        # Yet recent logs should be always displayed.
        logs = LogEntry.objects.recent_for_job(self.job)
        self.assertTrue(logs)

    def test_config(self):
        params = {
            'sample_id': 0,
            'sample_url': 'test',
            'sample_screenshot': 'test',
        }
        log = LogEntry.objects.log(
            log_type=LOG_TYPE_NEW_SAMPLE_DONE,
            job=self.job,
            params=params,
        )

        self.assertTrue(log.get_single_text())
        self.assertTrue(log.get_plural_text())
        self.assertTrue(log.get_box())
        self.assertTrue(log.is_visible_to_users())

        log = LogEntry.objects.log(
            log_type=LOG_TYPE_JOB_INIT_START,
            job=self.job,
        )

        self.assertFalse(log.is_visible_to_users())
