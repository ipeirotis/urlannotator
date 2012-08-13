from django.test import TestCase
from django.contrib.auth.models import User

from urlannotator.main.models import Job
from urlannotator.sample_gathering.simple_gatherer import simple_gatherer
from urlannotator.classification.models import ClassifiedSample


class testSampleGatherer(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')

        self.job = Job.objects.create_active(
            account=self.u.get_profile(),
            no_of_urls=30,
            gold_samples=[
                {'url':'google.com', 'label':'Yes'},
                {'url':'wikipedia.org', 'label':'Yes'},
                {'url':'http://www.dec.ny.gov/animals/9358.html', 'label':'Yes'},
                {'url':'http://www.enchantedlearning.com/subjects/mammals/raccoon/Raccoonprintout.shtml', 'label':'Yes'},
            ]
        )
        self.job.activate()
        self.job.set_classifier_trained()

    def testSampleGatherer(self):
        self.assertEqual(ClassifiedSample.objects.all().count(), 4)
        simple_gatherer.delay()
        self.assertEqual(ClassifiedSample.objects.all().count(), 24)
        simple_gatherer.delay()
        self.assertEqual(ClassifiedSample.objects.all().count(), 34)
