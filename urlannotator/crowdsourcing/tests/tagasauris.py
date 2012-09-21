from django.test import TestCase
from django.conf import settings
from django.contrib.auth.models import User

from celery import task

from urlannotator.main.models import Job, Sample
from urlannotator.crowdsourcing.tagasauris_helper import (make_tagapi_client,
    create_job, sample_to_mediaobject)
from urlannotator.crowdsourcing.models import SampleMapping, TagasaurisJobs
from urlannotator.flow_control.test import ToolsMockedMixin
from urlannotator.flow_control import send_event


class TagasaurisHelperTest(ToolsMockedMixin, TestCase):

    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')
        self.job = Job.objects.create_active(
            title='test_tagapi_client',
            description='test_description',
            no_of_urls=2,
            account=self.u.get_profile(),
            gold_samples=[{'url': '10clouds.com', 'label': 'Yes'}])
        self.sample = Sample.objects.all()[0]

        self.tc = make_tagapi_client()

    def testCreateJob(self):
        voting_key, voting_hit = create_job(self.tc, self.job,
            settings.TAGASAURIS_SAMPLE_GATHERER_WORKFLOW)
        self.assertEqual(len(voting_hit), 32)
        self.assertEqual(len(voting_key), 32)

    def testSampleConvertion(self):
        self.sample.screenshot = 'test_123'
        mo = sample_to_mediaobject(self.sample)
        self.assertEqual(len(mo['id']), 32)
        self.assertEqual(mo['url'], self.sample.screenshot)
        self.assertEqual(mo['mimetype'], 'image/png')


class TagasaurisSampleVotingTest(ToolsMockedMixin, TestCase):

    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')
        self.job = Job.objects.create_active(
            title='test_tagapi_client',
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
