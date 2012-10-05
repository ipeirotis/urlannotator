import json

from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User

from urlannotator.main.models import Job, Sample
from urlannotator.flow_control.test import ToolsMockedMixin


class TagasaurisNotifyResourceTests(ToolsMockedMixin, TestCase):

    def setUp(self):
        self.api_url = '/api/v1/'
        self.user = User.objects.create_user(username='testing',
            password='test')
        self.c = Client()

    def testVerifyFromTagasauris(self):
        job = Job.objects.create_active(
            account=self.user.get_profile(),
            gold_samples=json.dumps([{'url': 'google.com', 'label': 'Yes'}]),
            same_domain_allowed=2,
            no_of_urls=10,
        )

        worker_id = 1234

        # Verifying first url (and adding)
        newest_url = 'google.com/1'
        data = {
            'url': newest_url,
            'worker_id': worker_id,
        }

        resp = self.c.post('%ssample/verify/%s/?format=json'
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

        resp = self.c.post('%ssample/verify/%s/?format=json'
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

        resp = self.c.post('%ssample/verify/%s/?format=json'
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
            gold_samples=json.dumps([{'url': 'google.com', 'label': 'Yes'}]),
            same_domain_allowed=20,
            no_of_urls=2,
        )

        worker_id = 1234

        # Verifying first url (and adding). We need one more.
        newest_url = 'google.com/1'
        data = {
            'url': newest_url,
            'worker_id': worker_id,
        }

        resp = self.c.post('%ssample/verify/%s/?format=json'
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

        resp = self.c.post('%ssample/verify/%s/?format=json'
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
