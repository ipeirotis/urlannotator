import time
import mock

from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.contrib.auth.models import User

from urlannotator.main.models import Sample, Job, Worker, LABEL_YES, LABEL_NO
from urlannotator.classification.classifiers import (Classifier247,
    Classifier as ClassifierObject, ClassifierTrainingCriticalError,
    ClassifierTrainingError, CLASS_TRAIN_STATUS_DONE)
from urlannotator.classification.models import (TrainingSet, Classifier,
    ClassifiedSample, ClassifierPerformance)
from urlannotator.classification.factories import classifier_factory
from urlannotator.classification.event_handlers import process_votes
from urlannotator.crowdsourcing.event_handlers import initialize_external_jobs
from urlannotator.crowdsourcing.models import WorkerQualityVote
from urlannotator.flow_control.test import FlowControlMixin, ToolsMockedMixin
from urlannotator.flow_control import send_event
from urlannotator.logging.models import LogEntry
from urlannotator.logging.settings import (
    LOG_TYPE_CLASSIFIER_TRAINING_ERROR,
    LOG_TYPE_CLASSIFIER_FATAL_TRAINING_ERROR)


class Classifier247Tests(ToolsMockedMixin, TestCase):

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

    def testTrainingErrors(self):
        training_set = self.job.trainingset_set.all()[0]

        def retryException(self, *args, **kwargs):
            self.test = getattr(self, 'test', 0)
            if not self.test:
                self.test = 1
                raise ClassifierTrainingError('test')
            else:
                return CLASS_TRAIN_STATUS_DONE

        def criticalError(self, *args, **kwargs):
            raise ClassifierTrainingCriticalError('test')

        # Lower training wait time.
        target = 'urlannotator.classification.classifiers.CLASS247_TRAIN_STEP'
        patch_time = mock.patch(target, new=1)
        patch_time.start()

        target = 'urlannotator.classification.classifiers.SimpleClassifier.get_train_status'

        # Test retry-safe error
        patch = mock.patch(target, new=retryException)
        patch.start()
        self.job.unset_classifier_trained()
        self.classifier247.train(training_set.training_samples.all())
        patch.stop()
        job = Job.objects.get(id=self.job.id)
        self.assertTrue(job.is_classifier_trained())
        self.assertEqual(LogEntry.objects.filter(
            job=job,
            log_type=LOG_TYPE_CLASSIFIER_TRAINING_ERROR,
        ).count(), 1)

        log = LogEntry.objects.get(
            job=job,
            log_type=LOG_TYPE_CLASSIFIER_TRAINING_ERROR,
        )

        # Test log entry values
        console_text = ('Error while training classifier for job (%d)'
                       ' - %s.') % (job.id, 'test')
        self.assertEqual(log.get_console_text(), console_text)

        # Test critical error
        patch = mock.patch(target, new=criticalError)
        patch.start()
        self.job.unset_classifier_trained()
        self.classifier247.train(training_set.training_samples.all())
        patch.stop()
        job = Job.objects.get(id=self.job.id)
        self.assertFalse(job.is_classifier_trained())
        self.assertEqual(LogEntry.objects.filter(
            job=job,
            log_type=LOG_TYPE_CLASSIFIER_FATAL_TRAINING_ERROR,
        ).count(), 1)

        log = LogEntry.objects.get(
            job=job,
            log_type=LOG_TYPE_CLASSIFIER_FATAL_TRAINING_ERROR,
        )

        # Test log entry values
        console_text = ('Fatal error while training classifier for job '
                       '(%d) - %s.') % (job.id, 'test')
        self.assertEqual(log.get_console_text(), console_text)

        # What if someone forgets to provide retrying behaviour of train class?
        # Just log it and abort.
        target = 'urlannotator.classification.classifiers.Classifier247._train'

        patch = mock.patch(target, new=retryException)
        patch.start()
        self.job.unset_classifier_trained()
        self.classifier247.train(training_set.training_samples.all())
        patch.stop()
        job = Job.objects.get(id=self.job.id)
        self.assertFalse(job.is_classifier_trained())
        self.assertEqual(LogEntry.objects.filter(
            job=job,
            log_type=LOG_TYPE_CLASSIFIER_TRAINING_ERROR,
        ).count(), 2)

        patch_time.stop()


class ClassifierTests(TestCase):
    def testClassifier(self):
        classifier = ClassifierObject()

        self.assertRaises(NotImplementedError, classifier.train)
        self.assertRaises(NotImplementedError, classifier.update, [0])
        self.assertRaises(NotImplementedError, classifier.classify, [0])
        self.assertRaises(NotImplementedError, classifier.analyze)
        self.assertRaises(NotImplementedError, classifier.get_train_status)
        self.assertRaises(NotImplementedError, classifier.classify_with_info, [0])


class SimpleClassifierTests(ToolsMockedMixin, TestCase):

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


class TrainingSetManagerTests(ToolsMockedMixin, TestCase):

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


class ClassifierPerformanceTests(ToolsMockedMixin, TestCase):
    def testPerformance(self):
        u = User.objects.create_user(username='testing', password='test')

        job = Job.objects.create_active(
            account=u.get_profile(),
            gold_samples=[{'url': '10clouds.com', 'label': 'Yes'}],
        )

        self.assertTrue(ClassifierPerformance.objects.latest_for_job(job))
        ClassifierPerformance.objects.all().delete()
        self.assertFalse(ClassifierPerformance.objects.latest_for_job(job))


class ClassifiedSampleTests(ToolsMockedMixin, TestCase):
    def testClassified(self):
        u = User.objects.create_user(username='testing', password='test')

        job = Job.objects.create_active(
            account=u.get_profile(),
            gold_samples=[{'url': '10clouds.com', 'label': 'Yes'}],
        )
        with self.assertRaises(KeyError):
            ClassifiedSample.objects.create_by_owner(job=job)
        cs = ClassifiedSample.objects.create_by_owner(
            job=job,
            url='http://google.com',
        )
        # Refresh the Classified Sample
        cs = ClassifiedSample.objects.get(id=cs.id)
        self.assertFalse(cs.is_pending())
        self.assertTrue(cs.is_successful())
        # Sample created by job owner - None worker.
        self.assertEqual(cs.get_source_worker(), None)


class ClassifierFactoryTests(ToolsMockedMixin, TestCase):

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
        cs = ClassifiedSample.objects.create_by_owner(
            job=job,
            url='http://google.com',
        )
        cs = ClassifiedSample.objects.get(id=cs.id)
        self.assertTrue(factory.classify(cs))


class LongTrainingTest(FlowControlMixin, TransactionTestCase):
    def setUp(self):
        self.u = User.objects.create_user(username='test', password='test')

    def get_flow_definition(self):
        old = super(LongTrainingTest, self).get_flow_definition()
        return [entry for entry in old if entry[1] != initialize_external_jobs]

    def testLongTraining(self):
        job = Job.objects.create_active(
            account=self.u.get_profile(),
            gold_samples=[{'url': '10clouds.com', 'label': 'Yes'}])
        time.sleep(2)

        # Refresh our job object
        job = Job.objects.get(id=job.id)
        self.assertTrue(job.is_classifier_trained())

    def tearDown(self):
        self.u.delete()


class ProcessVotesTest(FlowControlMixin, TransactionTestCase):

    flow_definition = [
        (r'^EventProcessVotes$', process_votes),
    ]

    def setUp(self):
        self.user = User.objects.create_user(username='test', password='test')
        self.job = Job.objects.create(
            account=self.user.get_profile()
        )
        self.job.activate()
        self.sample = Sample.objects.create(
            source_val='asd',
            job=self.job,
            url=""
        )
        self.workers = [Worker.objects.create_odesk(external_id=x)
            for x in xrange(10)]

    def testVotesProcess(self):

        def newVote(worker, label):
            return WorkerQualityVote.objects.new_vote(
                sample=self.sample,
                worker=worker,
                label=label
            )

        newVote(self.workers[0], LABEL_YES)
        newVote(self.workers[1], LABEL_YES)
        newVote(self.workers[2], LABEL_YES)

        send_event('EventProcessVotes')

        ts = TrainingSet.objects.newest_for_job(self.job)
        self.assertEqual(len(ts.training_samples.all()), 1)

        training_sample = ts.training_samples.all()[0]
        self.assertEqual(training_sample.label, LABEL_YES)

        newVote(self.workers[3], LABEL_NO)
        newVote(self.workers[4], LABEL_NO)
        newVote(self.workers[5], LABEL_NO)
        newVote(self.workers[6], LABEL_NO)

        send_event('EventProcessVotes')

        ts = TrainingSet.objects.newest_for_job(self.job)
        self.assertEqual(len(ts.training_samples.all()), 1)

        training_sample = ts.training_samples.all()[0]
        self.assertEqual(training_sample.label, LABEL_NO)

    def tearDown(self):
        self.user.delete()
        for w in self.workers:
            w.delete()
        self.job.delete()
        self.sample.delete()
