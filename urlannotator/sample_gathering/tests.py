from django.test import TestCase

from urlannotator.main.models import Job, Account
from urlannotator.sample_gathering.simple_gatherer import simple_gatherer
from urlannotator.classification.models import ClassifiedSample


class testSampleGatherer(TestCase):
    fixtures = ['sample_test_fixture.json']

    def setUp(self):
        acc = Account.objects.all()[0]
        self.job = Job.objects.create_active(
            account=acc,
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
