import json

from django.test import TestCase
from django.test.utils import override_settings
from django.contrib.auth.models import User

from urlannotator.main.models import Sample, Job
from urlannotator.classification.classifiers import (SimpleClassifier,
    GooglePredictionClassifier, Classifier247)
from urlannotator.classification.models import (TrainingSet, Classifier,
    ClassifiedSample)
from urlannotator.classification.factories import classifier_factory
from urlannotator.classification.management.commands.google_monitor import (
    GoogleTrainingMonitor)


class Classifier247Tests(TestCase):

    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')

        self.job = Job.objects.create_active(
            account=self.u.get_profile(),
            gold_samples=[{'url': '10clouds.com', 'label': 'Yes'}])

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

        self.classifier247 = classifier_factory.create_classifier(
            job_id=self.job.id,
        )

    def testReadClassifier247(self):
        test_sample = self.classified[0]
        self.assertNotEqual(self.classifier247.classify(test_sample), None)
        self.assertNotEqual(self.classifier247.classify_with_info(test_sample),
            None)


class SimpleClassifierTests(TestCase):

    @override_settings(JOB_DEFAULT_CLASSIFIER='SimpleClassifier')
    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')

        self.job = Job.objects.create_active(
            account=self.u.get_profile(),
            gold_samples=[{'url': '10clouds.com', 'label': 'Yes'}])

        self.job = Job.objects.all()[0]

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
        sc_id = classifier_factory.initialize_classifier(
            job_id=self.job.id,
            classifier_name='SimpleClassifier',
        )
        sc = classifier_factory.create_classifier_from_id(sc_id)

        training_set = TrainingSet.objects.newest_for_job(self.job)

        sc.train(set_id=training_set.id)

        test_sample = self.classified[0]
        # Classifier already trained
        self.assertNotEqual(sc.classify(test_sample), None)
        self.assertNotEqual(sc.classify_with_info(test_sample), None)


class TrainingSetManagerTests(TestCase):

    def testTrainingSet(self):
        job = Job()
        self.assertEqual(TrainingSet.objects.newest_for_job(job), None)

        u = User.objects.create_user(username='testing', password='test')

        job = Job.objects.create_active(
            account=u.get_profile(),
            gold_samples=[{'url': '10clouds.com', 'label': 'Yes'}])

        ts = TrainingSet(job=job)
        ts.save()
        self.assertEqual(TrainingSet.objects.newest_for_job(job).job.id,
            job.id)


class ClassifierFactoryTests(TestCase):

    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')

        self.job = Job.objects.create_active(
            account=self.u.get_profile(),
            gold_samples=[{'url': '10clouds.com', 'label': 'Yes'}])

    def testClassifierFactory(self):
        job = Job.objects.create_active(
            account=self.u.get_profile(),
            gold_samples=[{'url': '10clouds.com', 'label': 'Yes'}],
        )
        factory = classifier_factory.create_classifier(job.id)
        self.assertEqual(factory.__class__, Classifier247)
        self.assertEqual(Classifier.objects.filter(
            job=job,
            type='SimpleClassifier',
        ).count(), 2)
        cs = ClassifiedSample.objects.all()[0]
        self.assertTrue(factory.classify(cs))


class GoogleMonitorTests(TestCase):

    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')

        self.job = Job.objects.create_active(
            account=self.u.get_profile(),
            gold_samples=[{'url': '10clouds.com', 'label': 'Yes'}])

    def testGoogleMonitor(self):
        monitor = GoogleTrainingMonitor()

        entry = Classifier.objects.get(job=self.job, main=True)
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
        entry = Classifier.objects.get(job=self.job, main=True)
        params = entry.parameters
        self.assertFalse('training' in params)
        job = Job.objects.get(id=self.job.id)
        self.assertTrue(job.is_classifier_trained())
