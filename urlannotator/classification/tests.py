from django.test import TestCase
from django.contrib.auth.models import User

from urlannotator.main.models import Sample, Job
from urlannotator.classification.classifiers import (SimpleClassifier,
    Classifier247)
from urlannotator.classification.models import TrainingSet


class Classifier247Tests(TestCase):

    def setUp(self):
        self.train_data = [
            Sample(text='Mechanical squirrel screwdriver over car',
                label='Yes'),
            Sample(text='Screwdriver fix mechanical bike bolts', label='Yes'),
            Sample(text='Brown banana apple pinapple potato', label='No'),
            Sample(text='apple pinapple potato', label='No'),
            Sample(text='Hippo tree over lagoon', label='No'),
            Sample(text='Green tan with true fox', label='No')
        ]

        self.classifier247 = Classifier247(SimpleClassifier,
            description='Test classifier', classes=['label'])

    def testReadClassifier247(self):
        test_sample = Sample(text='Scottish whisky banana apple pinapple')
        self.assertEqual(self.classifier247.classify(test_sample), None)
        self.assertEqual(self.classifier247.classify_with_info(test_sample),
            None)
        self.classifier247.train(self.train_data)
        self.assertNotEqual(self.classifier247.classify(test_sample), None)


class SimpleClassifierTests(TestCase):
    def testSimpleClassifier(self):
        train_data = [
            Sample(text='Mechanical squirrel screwdriver over car',
                label='Yes'),
            Sample(text='Screwdriver fix mechanical bike bolts', label='Yes'),
            Sample(text='Brown banana apple pinapple potato', label='No'),
            Sample(text='apple pinapple potato', label='No'),
            Sample(text='Hippo tree over lagoon', label='No'),
            Sample(text='Green tan with true fox', label='No')
        ]

        sc = SimpleClassifier(description='Test classifier', classes=['label'])
        # Tests without training
        test_sample = Sample(text='Scottish whisky banana apple pinapple')
        self.assertEqual(sc.classify(test_sample), None)
        self.assertEqual(sc.classify_with_info(test_sample), None)
        sc.train(train_data)
        self.assertNotEqual(sc.classify(test_sample), None)


class TrainingSetManagerTests(TestCase):
    def testTrainingSet(self):
        job = Job()
        self.assertEqual(TrainingSet.objects.newest_for_job(job), None)

        u = User.objects.create_user(username='test2', password='test')
        job = Job(account=u.get_profile())
        job.save()

        ts = TrainingSet(job=job)
        ts.save()
        self.assertEqual(TrainingSet.objects.newest_for_job(job).job.id,
            job.id)
