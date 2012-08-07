import json

from django.test import TestCase
from django.contrib.auth.models import User

from urlannotator.main.models import Sample, Job, ClassifiedSample
from urlannotator.classification.classifiers import (SimpleClassifier,
    Classifier247, GooglePredictionClassifier)
from urlannotator.classification.models import TrainingSet, Classifier
from urlannotator.classification.factories import classifier_factory
from urlannotator.classification.management.commands.google_monitor import (
    GoogleTrainingMonitor)


class Classifier247Tests(TestCase):

    def setUp(self):
        self.u = User.objects.create_user(username='test', password='test')

        self.job = Job(account=self.u.get_profile())
        self.job.save()

        self.train_data = [
            Sample(job=self.job, source_type='',
                text='Mechanical squirrel screwdriver over car'),
            Sample(job=self.job, source_type='',
                text='Screwdriver fix mechanical bike bolts'),
            Sample(job=self.job, source_type='',
                text='Brown banana apple pinapple potato'),
            Sample(job=self.job, source_type='',
                text='apple pinapple potato'),
            Sample(job=self.job, source_type='',
                text='Hippo tree over lagoon'),
            Sample(job=self.job, source_type='',
                text='Green tan with true fox')
        ]
        self.labels = ['Yes', 'Yes', 'No', 'No', 'No', 'No']
        self.classified = []
        for idx, sample in enumerate(self.train_data):
            self.classified.append(ClassifiedSample.objects.create(
                job=self.job,
                sample=sample,
                label=self.labels[idx]
            ))

        self.classifier247 = Classifier247(SimpleClassifier,
            description='Test classifier', classes=['label'])

    def testReadClassifier247(self):
        test_sample = Sample(job=self.job, source_type='',
            text='Scottish whisky banana apple pinapple')
        self.assertEqual(self.classifier247.classify(test_sample), None)
        self.assertEqual(self.classifier247.classify_with_info(test_sample),
            None)
        self.classifier247.train(self.classified)
        self.assertNotEqual(self.classifier247.classify(test_sample), None)


class SimpleClassifierTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='test', password='test')

        self.job = Job(account=self.u.get_profile())
        self.job.save()

        self.train_data = [
            Sample(job=self.job, source_type='',
                text='Mechanical squirrel screwdriver over car'),
            Sample(job=self.job, source_type='',
                text='Screwdriver fix mechanical bike bolts'),
            Sample(job=self.job, source_type='',
                text='Brown banana apple pinapple potato'),
            Sample(job=self.job, source_type='',
                text='apple pinapple potato'),
            Sample(job=self.job, source_type='',
                text='Hippo tree over lagoon'),
            Sample(job=self.job, source_type='',
                text='Green tan with true fox')
        ]
        self.labels = ['Yes', 'Yes', 'No', 'No', 'No', 'No']
        self.classified = []
        for idx, sample in enumerate(self.train_data):
            self.classified.append(ClassifiedSample.objects.create(
                job=self.job,
                sample=sample,
                label=self.labels[idx]
            ))

    def testSimpleClassifier(self):
        sc = SimpleClassifier(description='Test classifier', classes=['label'])
        # Tests without training
        test_sample = Sample(job=self.job, source_type='',
            text='Scottish whisky banana apple pinapple')
        self.assertEqual(sc.classify(test_sample), None)
        self.assertEqual(sc.classify_with_info(test_sample), None)
        sc.train(self.classified)
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


class ClassifierFactoryTests(TestCase):

    def setUp(self):
        self.u = User.objects.create_user(username='test', password='1')
        # # Clean cached classifiers
        # classifier_factory.cache.clear()

    def testClassifierFactory(self):
        Job.objects.create_active(account=self.u.get_profile())
        classifier_factory.initialize_classifier(1, 'SimpleClassifier')
        factory = classifier_factory.create_classifier(1)
        self.assertEqual(factory.__class__, SimpleClassifier)


class GoogleMonitorTests(TestCase):

    def setUp(self):
        self.u = User.objects.create_user(username='test', password='1')
        # Clean cached classifiers
        classifier_factory.cache.clear()

    def testGoogleMonitor(self):
        job = Job.objects.create_active(account=self.u.get_profile())
        monitor = GoogleTrainingMonitor()

        entry = Classifier.objects.get(job=job)
        entry.type = 'GooglePredictionClassifier'
        entry.parameters = json.dumps({'model': 'test', 'training': 'RUNNING'})
        entry.save()
        params = entry.parameters
        self.assertIn('training', params)

        # Mock classifier's get_train_status. It is async, and we can't really
        # test it.
        old_status = GooglePredictionClassifier.get_train_status
        GooglePredictionClassifier.get_train_status = lambda x: 'DONE'
        old_analyze = GooglePredictionClassifier.analyze
        GooglePredictionClassifier.analyze = lambda x: {
            'modelDescription': {
                'confusionMatrix': {
                    'Yes': {
                        'Yes': 5.0,
                        'No': 3.0,
                    },
                    'No': {
                        'Yes': 2.0,
                        'No': 7.0,
                    }
                }
            }
        }
        monitor.run()

        GoogleTrainingMonitor.run = old_status
        entry = Classifier.objects.get(job=job)
        params = entry.parameters
        self.assertFalse('training' in params)
        job = Job.objects.get(id=job.id)
        self.assertTrue(job.is_classifier_trained())

        # Clean cached classifiers
        classifier_factory.cache.clear()
