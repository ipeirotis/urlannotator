import mock
import json

from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User

from tagapi.error import TagasaurisApiException

from urlannotator.main.models import (Job, Sample, LABEL_NO, LABEL_YES,
    LABEL_BROKEN, Worker)
from urlannotator.flow_control.test import ToolsMockedMixin
from urlannotator.crowdsourcing.models import (SampleMapping,
    WorkerQualityVote, BeatTheMachineSample, TagasaurisJobs)


class TagasaurisSampleResourceTests(ToolsMockedMixin, TestCase):

    def setUp(self):
        self.api_url = '/api/v1/'
        self.user = User.objects.create_user(username='testing',
            password='test')
        self.c = Client()

    def testVerifyFromTagasauris(self):
        job = Job.objects.create_active(
            account=self.user.get_profile(),
            gold_samples=json.dumps([{'url': 'google.com', 'label': LABEL_YES}]),
            same_domain_allowed=2,
            no_of_urls=10,
        )

        worker_id = '1234'

        # Verifying first url (and adding)
        newest_url = 'google.com/1'
        data = {
            'url': newest_url,
            'worker_id': worker_id,
        }

        resp = self.c.post('%ssample/add/tagasauris/%s/?format=json'
            % (self.api_url, job.id), json.dumps(data), "text/json")
        self.assertEqual(resp.status_code, 200)

        resp_dict = json.loads(resp.content)

        self.assertTrue('result' in resp_dict.keys())
        self.assertTrue('all' in resp_dict.keys())

        self.assertEqual('added', resp_dict['result'])
        self.assertEqual(False, resp_dict['all'])

        self.assertEqual(Sample.objects.filter(
            job=job, url=Sample.sanitize_url(newest_url)).count(), 1)

        # This time verification should fail becaufe of too many urls from same
        # domain
        newest_url = 'google.com/2'
        data = {
            'url': newest_url,
            'worker_id': worker_id,
        }

        resp = self.c.post('%ssample/add/tagasauris/%s/?format=json'
            % (self.api_url, job.id), json.dumps(data), "text/json")
        self.assertEqual(resp.status_code, 200)

        resp_dict = json.loads(resp.content)

        self.assertTrue('result' in resp_dict.keys())
        self.assertTrue('all' in resp_dict.keys())

        self.assertEqual('domain duplicate', resp_dict['result'])
        self.assertEqual(False, resp_dict['all'])

        self.assertEqual(Sample.objects.filter(
            job=job, url=Sample.sanitize_url(newest_url)).count(), 0)

        # This time verification should fail becaufe of duplicated url (look at
        # golden sample)
        newest_url = 'google.com'
        data = {
            'url': newest_url,
            'worker_id': worker_id,
        }

        resp = self.c.post('%ssample/add/tagasauris/%s/?format=json'
            % (self.api_url, job.id), json.dumps(data), "text/json")
        self.assertEqual(resp.status_code, 200)

        resp_dict = json.loads(resp.content)

        self.assertTrue('result' in resp_dict.keys())
        self.assertTrue('all' in resp_dict.keys())

        self.assertEqual('duplicate', resp_dict['result'])
        self.assertEqual(False, resp_dict['all'])

        self.assertEqual(Sample.objects.filter(
            job=job, url=Sample.sanitize_url(newest_url)).count(), 1)

    def testVerifyFromTagasaurisLimit(self):
        job = Job.objects.create_active(
            account=self.user.get_profile(),
            gold_samples=json.dumps([{'url': 'google.com', 'label': LABEL_YES}]),
            same_domain_allowed=20,
            no_of_urls=2,
        )

        worker_id = '1234'

        # Verifying first url (and adding). We need one more.
        newest_url = 'google.com/1'
        data = {
            'url': newest_url,
            'worker_id': worker_id,
        }

        resp = self.c.post('%ssample/add/tagasauris/%s/?format=json'
            % (self.api_url, job.id), json.dumps(data), "text/json")
        self.assertEqual(resp.status_code, 200)

        resp_dict = json.loads(resp.content)

        self.assertTrue('result' in resp_dict.keys())
        self.assertTrue('all' in resp_dict.keys())

        self.assertEqual('added', resp_dict['result'])
        self.assertEqual(False, resp_dict['all'])

        self.assertEqual(Sample.objects.filter(
            job=job, url=Sample.sanitize_url(newest_url)).count(), 1)

        # Verifying second url. Gathering should be completed.
        newest_url = 'google.com/2'
        data = {
            'url': newest_url,
            'worker_id': worker_id,
        }

        resp = self.c.post('%ssample/add/tagasauris/%s/?format=json'
            % (self.api_url, job.id), json.dumps(data), "text/json")
        self.assertEqual(resp.status_code, 200)

        resp_dict = json.loads(resp.content)

        self.assertTrue('result' in resp_dict.keys())
        self.assertTrue('all' in resp_dict.keys())

        self.assertEqual('added', resp_dict['result'])
        self.assertEqual(True, resp_dict['all'])

        self.assertEqual(Sample.objects.filter(
            job=job, url=Sample.sanitize_url(newest_url)).count(), 1)

        self.assertEqual(job.get_urls_collected(), job.no_of_urls)

        # Verifying third url. Gathering should be completed but url won't be
        # added.
        newest_url = 'google.com/3'
        data = {
            'url': newest_url,
            'worker_id': worker_id,
        }

        resp = self.c.post('%ssample/add/tagasauris/%s/?format=json'
            % (self.api_url, job.id), json.dumps(data), "text/json")
        self.assertEqual(resp.status_code, 200)

        resp_dict = json.loads(resp.content)

        self.assertTrue('result' in resp_dict.keys())
        self.assertTrue('all' in resp_dict.keys())

        self.assertEqual('', resp_dict['result'])
        self.assertEqual(True, resp_dict['all'])

        self.assertEqual(Sample.objects.filter(
            job=job, url=Sample.sanitize_url(newest_url)).count(), 0)

        self.assertEqual(job.get_urls_collected(), job.no_of_urls)

    def testVerifyFromTagasaurisErrors(self):
        job = Job.objects.create_active(
            account=self.user.get_profile(),
            gold_samples=json.dumps([{'url': 'google.com', 'label': LABEL_YES}]),
            same_domain_allowed=2,
            no_of_urls=10,
        )

        worker_id = '1234'

        # Error on not existing job.
        newest_url = 'google.com/1'
        data = {
            'url': newest_url,
            'worker_id': worker_id,
        }

        resp = self.c.post('%ssample/add/tagasauris/%s/?format=json'
            % (self.api_url, 1234567), json.dumps(data), "text/json")
        self.assertNotEqual(resp.status_code, 200)

        resp_dict = json.loads(resp.content)

        self.assertTrue('error' in resp_dict.keys())
        self.assertEqual(Sample.objects.filter(
            url=Sample.sanitize_url(newest_url)).count(), 0)

        # Error on wrong post data (not json).
        newest_url = 'google.com/1'
        data = {
            'url': newest_url,
            'worker_id': worker_id,
        }

        resp = self.c.post('%ssample/add/tagasauris/%s/?format=json'
            % (self.api_url, job.id), data)
        self.assertNotEqual(resp.status_code, 200)

        resp_dict = json.loads(resp.content)

        self.assertTrue('error' in resp_dict.keys())
        self.assertEqual(Sample.objects.filter(
            url=Sample.sanitize_url(newest_url)).count(), 0)

        # Error on wrong post data (parameters errors).
        newest_url = 'google.com/1'
        data = {
            'worker_id': worker_id,
        }

        resp = self.c.post('%ssample/add/tagasauris/%s/?format=json'
            % (self.api_url, job.id), json.dumps(data), "text/json")
        self.assertNotEqual(resp.status_code, 200)

        resp_dict = json.loads(resp.content)

        self.assertTrue('error' in resp_dict.keys())
        self.assertEqual(Sample.objects.filter(
            url=Sample.sanitize_url(newest_url)).count(), 0)

        newest_url = 'google.com/1'
        data = {
            'url': newest_url,
        }

        resp = self.c.post('%ssample/add/tagasauris/%s/?format=json'
            % (self.api_url, job.id), json.dumps(data), "text/json")
        self.assertNotEqual(resp.status_code, 200)

        resp_dict = json.loads(resp.content)

        self.assertTrue('error' in resp_dict.keys())
        self.assertEqual(Sample.objects.filter(
            url=Sample.sanitize_url(newest_url)).count(), 0)


class TagasaurisVoteResourceTests(ToolsMockedMixin, TestCase):

    def setUp(self):
        self.api_url = '/api/v1/'
        self.user = User.objects.create_user(username='testing',
            password='test')
        self.c = Client()

    def testAddFromTagasaurisErrors(self):
        job = Job.objects.create_active(
            account=self.user.get_profile(),
            gold_samples=json.dumps([{'url': 'google.com', 'label': LABEL_YES}]),
        )

        data = {}

        resp = self.c.post('%svote/add/tagasauris/%s/?format=json'
            % (self.api_url, job.id), json.dumps(data), "text/json")
        resp_dict = json.loads(resp.content)
        self.assertTrue('error' in resp_dict.keys())

    def testAddFromTagasauris(self):
        job = Job.objects.create_active(
            account=self.user.get_profile(),
            gold_samples=json.dumps([{'url': 'google.com', 'label': LABEL_YES}]),
        )

        sample = Sample.objects.all()[0]

        ext_id_1 = 1
        SampleMapping(
            sample=sample,
            external_id=ext_id_1,
            crowscourcing_type=SampleMapping.TAGASAURIS,
        ).save()

        data = {
            'results': {
                1: {ext_id_1: [{'tag': 'yes'}, ]},
                2: {ext_id_1: [{'tag': 'no'}, ]},
                3: {ext_id_1: [{'tag': 'broken'}, ]},
                4: {ext_id_1: [{'tag': 'unknown12234'}, ]},
            }
        }

        resp = self.c.post('%svote/add/tagasauris/%s/?format=json'
            % (self.api_url, job.id), json.dumps(data), "text/json")
        self.assertEqual(resp.status_code, 200)

        self.assertEqual(WorkerQualityVote.objects.all().count(), 3)
        self.assertEqual(WorkerQualityVote.objects.filter(
            sample=sample, label=LABEL_NO).count(), 1)
        self.assertEqual(WorkerQualityVote.objects.filter(
            sample=sample, label=LABEL_YES).count(), 1)
        self.assertEqual(WorkerQualityVote.objects.filter(
            sample=sample, label=LABEL_BROKEN).count(), 1)


class TagasaurisBTMResourceTests(ToolsMockedMixin, TestCase):

    def setUp(self):
        self.api_url = '/api/v1/'
        self.user = User.objects.create_user(username='testing',
            password='test')
        self.c = Client()

    def testAddBTMErrors(self):
        job = Job.objects.create_active(
            account=self.user.get_profile(),
            gold_samples=json.dumps([{'url': 'google.com', 'label': LABEL_YES}]),
        )

        data = {}
        resp = self.c.post('%sbtm/add/tagasauris/%s/?format=json'
            % (self.api_url, job.id), json.dumps(data), "text/json")
        resp_dict = json.loads(resp.content)
        self.assertTrue('error' in resp_dict.keys())
        self.assertNotEqual(resp.status_code, 200)

        data = {'url': '', 'label': '', 'worker_id': ''}
        resp = self.c.post('%sbtm/add/tagasauris/%s/?format=json'
            % (self.api_url, 123456), json.dumps(data), "text/json")
        resp_dict = json.loads(resp.content)
        self.assertTrue('error' in resp_dict.keys())
        self.assertNotEqual(resp.status_code, 200)

        data = {'url': '', 'label': '', 'worker_id': ''}
        resp = self.c.post('%sbtm/add/tagasauris/%s/?format=json'
            % (self.api_url, job.id), data)
        resp_dict = json.loads(resp.content)
        self.assertTrue('error' in resp_dict.keys())
        self.assertNotEqual(resp.status_code, 200)

    def testAddBTM(self):
        job = Job.objects.create_active(
            account=self.user.get_profile(),
            gold_samples=json.dumps([{'url': 'google.com', 'label': LABEL_NO}]),
        )

        worker_id = '1234'
        data = {
            'url': 'google.com',
            'worker_id': worker_id
        }

        resp = self.c.post('%sbtm/add/tagasauris/%s/?format=json'
            % (self.api_url, job.id), json.dumps(data), "text/json")
        self.assertEqual(resp.status_code, 200)

        resp_dict = json.loads(resp.content)

        self.assertTrue('request_id' in resp_dict.keys())
        self.assertTrue('status_url' in resp_dict.keys())

        self.assertEqual(BeatTheMachineSample.objects.all().count(), 1)

        # Because of eager celery we can check this:
        btm_sample = BeatTheMachineSample.objects.all()[0]
        self.assertEqual(resp_dict['request_id'], btm_sample.id)
        self.assertEqual(btm_sample.source_val, worker_id)

        # Not sure if I should test it here
        # self.assertEqual(btm_sample.expected_output, btm_sample.label)

    def testStatusBTMErrors(self):
        job = Job.objects.create_active(
            account=self.user.get_profile(),
            gold_samples=json.dumps([{'url': 'google.com', 'label': LABEL_YES}]),
        )

        classified_sample = BeatTheMachineSample.objects.create_by_worker(
            job=job,
            url='google.com',
            label='',
            expected_output=LABEL_YES,
            worker_id=123
        )

        data = {
            'request_id': classified_sample.id
        }
        resp = self.c.get('%sbtm/status/tagasauris/%s/?format=json'
            % (self.api_url, 123456), data)
        self.assertNotEqual(resp.status_code, 200)
        resp_dict = json.loads(resp.content)
        self.assertTrue('error' in resp_dict.keys())

        data = {
            'request_id': 1234567
        }
        resp = self.c.get('%sbtm/status/tagasauris/%s/?format=json'
            % (self.api_url, job.id), data)
        self.assertNotEqual(resp.status_code, 200)
        resp_dict = json.loads(resp.content)
        self.assertTrue('error' in resp_dict.keys())

    def testStatusBTM(self):
        job = Job.objects.create_active(
            account=self.user.get_profile(),
            gold_samples=json.dumps([{'url': 'google.com', 'label': LABEL_YES}]),
        )
        classified_sample = BeatTheMachineSample.objects.create_by_worker(
            job=job,
            url='google.com',
            label='',
            expected_output=LABEL_YES,
            worker_id=124
        )

        data = {
            'request_id': classified_sample.id
        }

        resp = self.c.get('%sbtm/status/tagasauris/%s/?format=json'
            % (self.api_url, job.id), data)
        self.assertEqual(resp.status_code, 200)

        resp_dict = json.loads(resp.content)

        self.assertTrue('status' in resp_dict.keys())
        self.assertTrue('points' in resp_dict.keys())
        self.assertTrue('btm_status' in resp_dict.keys())

    def testStartBtm(self):
        job = Job.objects.create_active(
            account=self.user.get_profile(),
            gold_samples=json.dumps([{'url': 'google.com', 'label': LABEL_YES}]),
        )

        TagasaurisJobs.objects.get_or_create(urlannotator_job=job)
        self.assertEqual(1, TagasaurisJobs.objects.count())

        job.start_btm("test topic", "test desc", 10, 5000)
        job.activate_btm()
        job = Job.objects.get(id=job.id)

        self.assertEqual(job.btm_status, job.BTMStatus.ACTIVE)
        self.assertEqual(10, job.btm_to_gather)
        self.assertFalse(job.add_filler_samples)
        self.assertEqual(5000, job.btm_points_to_cash)

        self.assertEqual(1, TagasaurisJobs.objects.count())
        tj = TagasaurisJobs.objects.all()[0]
        self.assertEqual(32, len(tj.beatthemachine_key))


class TagasaurisWorker(ToolsMockedMixin, TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testing',
            password='test')
        self.job = Job.objects.create_active(
            account=self.user.get_profile(),
            gold_samples=json.dumps(
                [{'url': 'google.com', 'label': LABEL_YES}]),
        )

        # Twitter worker on devel.tagasauris.com
        self.twitter_worker = Worker.objects.create_tagasauris(external_id=83)

        # Mturk worker on devel.tagasauris.com
        self.mturk_worker = Worker.objects.create_tagasauris(external_id=41)

    def testMessageSending(self):
        mocks = mock.patch('urlannotator.main.models.Worker._send_tagasauris_message',
            mock.MagicMock(side_effect=TagasaurisApiException('test')))

        with mocks:
            # Should invoke _send_tagasauris_message
            with self.assertRaises(TagasaurisApiException):
                self.twitter_worker.send_message("subject", "content")

        mocks = mock.patch('urlannotator.main.models.Worker._send_tagasauris_message',
            mock.MagicMock())

        with mocks:
            # Should invoke _send_tagasauris_message
            self.mturk_worker.send_message("test_subject", "test_content")

            # Checks if message contains all important data
            self.mturk_worker._prepare_bonus_notification(self.job)

            # Only prep + send.
            self.mturk_worker.send_bonus_notification(self.job)
