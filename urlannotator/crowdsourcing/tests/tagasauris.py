from django.test import TestCase
from django.conf import settings
from django.contrib.auth.models import User

from urlannotator.main.models import Job, Sample
from urlannotator.crowdsourcing.tagasauris_helper import (make_tagapi_client,
    create_job, sample_to_mediaobject)
from urlannotator.flow_control.test import ToolsMockedMixin


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
