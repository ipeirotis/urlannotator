import json

from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User

from celery import task

from urlannotator.main.models import Job, Sample
from urlannotator.crowdsourcing.tagasauris_helper import (make_tagapi_client,
    create_sample_gather, sample_to_mediaobject, stop_job)
from urlannotator.crowdsourcing.models import SampleMapping, TagasaurisJobs
from urlannotator.flow_control.test import ToolsMockedMixin, ToolsMocked
from urlannotator.flow_control import send_event
from urlannotator.classification.event_handlers import train


class TagasaurisHelperTest(ToolsMockedMixin, TestCase):

    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')
        self.job = Job.objects.create_active(
            title='urlannotator_test_tagapi_client',
            description='test_description',
            no_of_urls=2,
            account=self.u.get_profile(),
            gold_samples=[{'url': '10clouds.com', 'label': 'Yes'}])
        self.sample = Sample.objects.all()[0]

        self.tc = make_tagapi_client()

    def testCreateJob(self):
        voting_key, voting_hit = create_sample_gather(self.tc, self.job)
        self.assertEqual(len(voting_hit), 32)
        self.assertEqual(len(voting_key), 32)

    def testJobDistinctHID(self):
        voting_key_1, voting_hit_1 = create_sample_gather(self.tc, self.job)
        voting_key_2, voting_hit_2 = create_sample_gather(self.tc, self.job)
        self.assertNotEqual(voting_key_1, voting_key_2)
        self.assertNotEqual(voting_hit_1, voting_hit_2)

    def testSampleConvertion(self):
        self.sample.screenshot = 'test_123'
        mo = sample_to_mediaobject(self.sample)
        self.assertEqual(len(mo['id']), 32)
        self.assertEqual(mo['url'], self.sample.screenshot)
        self.assertEqual(mo['mimetype'], 'image/png')

    def testCreateAndStop(self):
        voting_key, voting_hit = create_sample_gather(self.tc, self.job)

        result = self.tc.get_job(external_id=voting_key)
        self.assertNotEqual(result['state'], 'stopped')

        stop_job(voting_key)

        result = self.tc.get_job(external_id=voting_key)
        self.assertEqual(result['state'], 'stopped')


class TagasaurisInApi(ToolsMockedMixin, TestCase):

    def setUp(self):
        self.api_url = '/api/v1/'
        self.user = User.objects.create_user(username='test', password='test')
        self.user.is_superuser = True
        self.user.save()

        self.c = Client()
        self.tc = make_tagapi_client()

        self.job = Job.objects.create_active(
            title='urlannotator_test_tagapi_client',
            description='test_description',
            no_of_urls=2,
            account=self.user.get_profile(),
            gold_samples=[{'url': '10clouds.com', 'label': 'Yes'}])

    def testCreateAndStop(self):
        # From closing tagasauris job view there is no difference between those
        # jobs - sample gather & voting
        voting_key, voting_hit = create_sample_gather(self.tc, self.job)
        sample_gathering_key, sample_gathering_hit = create_sample_gather(
            self.tc, self.job)

        TagasaurisJobs.objects.create(
            urlannotator_job=self.job,
            sample_gathering_key=sample_gathering_key,
            sample_gathering_hit=sample_gathering_hit,
            voting_key=voting_key,
            voting_hit=voting_hit
        )

        result = self.tc.get_job(external_id=voting_key)
        self.assertNotEqual(result['state'], 'stopped')
        result = self.tc.get_job(external_id=sample_gathering_key)
        self.assertNotEqual(result['state'], 'stopped')

        self.c.login(username='test', password='test')

        resp = self.c.get('%sadmin/job/%d/stop_sample_gathering/?format=json'
            % (self.api_url, self.job.id))

        self.assertEqual(resp.status_code, 200)
        array = json.loads(resp.content)
        self.assertEqual(array['result'], 'SUCCESS')
        result = self.tc.get_job(external_id=sample_gathering_key)
        self.assertEqual(result['state'], 'stopped')
        result = self.tc.get_job(external_id=voting_key)
        self.assertNotEqual(result['state'], 'stopped')

        resp = self.c.get('%sadmin/job/%d/stop_voting/?format=json'
            % (self.api_url, self.job.id))

        self.assertEqual(resp.status_code, 200)
        array = json.loads(resp.content)
        self.assertEqual(array['result'], 'SUCCESS')
        result = self.tc.get_job(external_id=sample_gathering_key)
        self.assertEqual(result['state'], 'stopped')
        result = self.tc.get_job(external_id=voting_key)
        self.assertEqual(result['state'], 'stopped')


class TagasaurisJobCreationChain(TestCase):

    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')

    def testSampleGatherOnJobCreation(self):

        @task()
        def mocked_task(*args, **kwargs):
            return True

        def eager_train(kwargs, *args, **kwds):
            train(set_id=kwargs['set_id'])

        mocks = [
            ('urlannotator.main.factories.web_content_extraction', mocked_task),
            ('urlannotator.main.factories.web_screenshot_extraction', mocked_task),
            ('urlannotator.classification.event_handlers.process_execute', eager_train),
        ]

        with ToolsMocked(mocks, add_hardcoded_mocks=False):
            self.job = Job.objects.create_active(
                title='urlannotator_test_tagapi_client',
                description='test_description',
                no_of_urls=2,
                account=self.u.get_profile(),
                gold_samples=[{'url': '10clouds.com', 'label': 'Yes'}])

        self.assertEqual(TagasaurisJobs.objects.count(), 1)
        tj = TagasaurisJobs.objects.all()[0]
        self.assertEqual(tj.urlannotator_job.id, self.job.id)
        self.assertEqual(len(tj.sample_gathering_key), 32)
        self.assertEqual(len(tj.sample_gathering_hit), 32)


class TagasaurisSampleVotingTest(ToolsMockedMixin, TestCase):

    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')
        self.job = Job.objects.create_active(
            title='urlannotator_test_tagapi_client',
            description='test_description',
            no_of_urls=2,
            account=self.u.get_profile(),
            gold_samples=[
                {'url': '10clouds.com/1', 'label': 'Yes'},
                {'url': '10clouds.com/2', 'label': 'Yes'},
                {'url': '10clouds.com/3', 'label': 'Yes'}
            ]
        )

        TagasaurisJobs.objects.create(urlannotator_job=self.job)

        for s in Sample.objects.all():
            s.screenshot = "http://www.10clouds.com/media/v1334047194.07/10c/images/10c_logo.png"
            s.save()

    def testEventSamplesVoting(self):
        self.assertEqual(TagasaurisJobs.objects.count(), 1)
        self.assertEqual(TagasaurisJobs.objects.all()[0].voting_key, None)
        self.assertEqual(TagasaurisJobs.objects.all()[0].voting_hit, None)

        send_event('EventSamplesVoting')

        self.assertEqual(SampleMapping.objects.count(), 3)

        self.assertEqual(SampleMapping.objects.all()[0].crowscourcing_type,
            SampleMapping.TAGASAURIS)
        self.assertEqual(len(SampleMapping.objects.all()[0].external_id), 32)

        self.assertEqual(TagasaurisJobs.objects.count(), 1)
        self.assertEqual(len(TagasaurisJobs.objects.all()[0].voting_key), 32)
        self.assertEqual(len(TagasaurisJobs.objects.all()[0].voting_hit), 32)


class TagasaurisJobsModelTest(ToolsMockedMixin, TestCase):

    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')
        self.job = Job.objects.create_active(
            title='urlannotator_test_tagapi_client',
            description='test_description',
            no_of_urls=2,
            account=self.u.get_profile(),
            gold_samples=[{'url': '10clouds.com', 'label': 'Yes'}])

    def testJobUrlsGeneration(self):

        tj = TagasaurisJobs.objects.create(urlannotator_job=self.job)

        self.assertEqual(tj.get_sample_gathering_url(), '')
        self.assertEqual(tj.get_voting_url(), '')

        tj.sample_gathering_hit = '123'
        tj.save()

        self.assertTrue(tj.sample_gathering_hit in
            tj.get_sample_gathering_url())
        self.assertTrue('tagasauris' in tj.get_sample_gathering_url())
        self.assertTrue('annotation' in tj.get_sample_gathering_url())
        self.assertEqual(tj.get_voting_url(), '')

        tj.voting_hit = '456'
        tj.save()

        self.assertTrue(tj.sample_gathering_hit in
            tj.get_sample_gathering_url())
        self.assertTrue('tagasauris' in tj.get_sample_gathering_url())
        self.assertTrue('annotation' in tj.get_sample_gathering_url())
        self.assertTrue(tj.voting_hit in
            tj.get_voting_url())
        self.assertTrue('tagasauris' in tj.get_voting_url())
        self.assertTrue('annotation' in tj.get_voting_url())
