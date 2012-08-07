from django.test import TestCase

from urlannotator.main.models import Job, ClassifiedSample, Account
from urlannotator.sample_gathering.simple_gatherer import simple_gatherer


class testSampleGatherer(TestCase):
    fixtures = ['init_test_fixture.json']

    def setUp(self):
        acc = Account.objects.all()[0]
        self.job = Job.objects.create_active(
            account=acc,
            no_of_urls=30,
            gold_samples=[{'url': 'google.com', 'label': 'Yes'}]
        )
        self.job.activate()
        self.job.set_classifier_trained()

    def testSampleGatherer(self):
        self.assertEqual(ClassifiedSample.objects.all().count(), 5)
        simple_gatherer.delay()
        self.assertEqual(ClassifiedSample.objects.all().count(), 25)
        simple_gatherer.delay()
        self.assertEqual(ClassifiedSample.objects.all().count(), 35)
