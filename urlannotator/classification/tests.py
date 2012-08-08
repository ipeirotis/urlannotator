import json

from django.test import TestCase
from django.contrib.auth.models import User

from urlannotator.main.models import Sample, Job
from urlannotator.classification.classifiers import (SimpleClassifier,
    Classifier247, GooglePredictionClassifier)
from urlannotator.classification.models import (TrainingSet, Classifier,
    ClassifiedSample)
from urlannotator.classification.factories import classifier_factory
from urlannotator.classification.management.commands.google_monitor import (
    GoogleTrainingMonitor)


class Classifier247Tests(TestCase):
    fixtures = ['classification_test_fixture.json']

    def setUp(self):
        self.u = User.objects.get(username='test')

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

        reader_id = classifier_factory.initialize_classifier(
            job_id=self.job.id,
            classifier_name='SimpleClassifier',
            prefix='reader',
            main=False,
        )
        writer_id = classifier_factory.initialize_classifier(
            job_id=self.job.id,
            classifier_name='SimpleClassifier',
            prefix='writer',
            main=False,
        )
        sc_reader = classifier_factory.create_classifier_from_id(reader_id)
        sc_writer = classifier_factory.create_classifier_from_id(writer_id)
        self.classifier247 = Classifier247(sc_reader, sc_writer)

    def testReadClassifier247(self):
        test_sample = self.classified[0]
        self.assertNotEqual(self.classifier247.classify(test_sample), None)
        self.assertNotEqual(self.classifier247.classify_with_info(test_sample),
            None)


class SimpleClassifierTests(TestCase):
    fixtures = ['classification_test_fixture.json']

    def setUp(self):
        self.u = User.objects.get(username='test')

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
        # Tests without training
        test_sample = self.classified[0]
        # Classifier already trained
        self.assertNotEqual(sc.classify(test_sample), None)
        self.assertNotEqual(sc.classify_with_info(test_sample), None)


class TrainingSetManagerTests(TestCase):
    fixtures = ['classification_test_fixture.json']

    def testTrainingSet(self):
        job = Job()
        self.assertEqual(TrainingSet.objects.newest_for_job(job), None)

        u = User.objects.get(username='test')

        job = Job.objects.all()[0]

        ts = TrainingSet(job=job)
        ts.save()
        self.assertEqual(TrainingSet.objects.newest_for_job(job).job.id,
            job.id)


class ClassifierFactoryTests(TestCase):
    fixtures = ['classification_test_fixture.json']

    def setUp(self):
        self.u = User.objects.get(username='test')

        self.job = Job.objects.all()

    def testClassifierFactory(self):
        job = Job.objects.create_active(
            account=self.u.get_profile(),
            gold_samples=[{'url': '10clouds.com', 'label': 'Yes'}],
        )
        factory = classifier_factory.create_classifier(job.id)
        self.assertEqual(factory.__class__, SimpleClassifier)
        cs = ClassifiedSample.objects.all()[0]
        self.assertTrue(factory.classify(cs))


class GoogleMonitorTests(TestCase):
    fixtures = ['classification_test_fixture.json']

    def setUp(self):
        self.u = User.objects.get(username='test')

        self.job = Job.objects.get(id=1)

    def testGoogleMonitor(self):
        monitor = GoogleTrainingMonitor()

        entry = Classifier.objects.get(job=self.job)
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
        entry = Classifier.objects.get(job=self.job)
        params = entry.parameters
        self.assertFalse('training' in params)
        job = Job.objects.get(id=self.job.id)
        self.assertTrue(job.is_classifier_trained())
