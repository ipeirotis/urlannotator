from django.test import TestCase

from urlannotator.main.models import (Job, Account,
    SpentStatistics, URLStatistics, ProgressStatistics)
from urlannotator.statistics.spent_monitor import spent_monitor
from urlannotator.statistics.url_monitor import url_monitor
from urlannotator.statistics.progress_monitor import progress_monitor
from urlannotator.statistics.stat_extraction import (extract_progress_stats,
    extract_url_stats, extract_spent_stats, extract_performance_stats,
    update_classifier_stats)
from urlannotator.classification.factories import classifier_factory
from urlannotator.classification.models import ClassifierPerformance


class testJobMonitors(TestCase):
    fixtures = ['init_test_fixture.json']

    def setUp(self):
        acc = Account.objects.all()[0]
        self.job = Job.objects.filter(account=acc)[0]
        self.job.activate()
        self.job.set_classifier_trained()

    def testMonitors(self):
        monitor_list = [
            (SpentStatistics, spent_monitor),
            (URLStatistics, url_monitor),
            (ProgressStatistics, progress_monitor),
        ]
        for cls, mon in monitor_list:
            self.assertEqual(cls.objects.filter(job=self.job).count(), 1)
            mon.delay()
            self.assertEqual(cls.objects.filter(job=self.job).count(), 2)


class testStatExtraction(TestCase):
    fixtures = ['init_test_fixture.json']

    def setUp(self):
        acc = Account.objects.all()[0]
        self.job = Job.objects.filter(account=acc)[0]
        self.job.activate()
        self.job.set_classifier_trained()

    def testExtraction(self):
        context = {}
        extractors = [
            (extract_performance_stats, 'performance_TPM'),
            (extract_performance_stats, 'performance_NPM'),
            (extract_performance_stats, 'performance_AUC'),
            (extract_spent_stats, 'spent_stats'),
            (extract_url_stats, 'url_stats'),
            (extract_progress_stats, 'progress_stats'),
        ]
        for ex in extractors:
            ex[0](self.job, context)
            self.assertIn('Date.UTC', context.get(ex[1], ''))

    def testMetrics(self):
        # Mock classifier.analyze() method so we don't use up resources
        classifier = classifier_factory.create_classifier(self.job.id)
        new_analyze = lambda: {
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

        classifier.analyze = new_analyze
        update_classifier_stats(classifier, self.job)
        self.assertEqual(ClassifierPerformance.objects.count(), 2)
        cp = ClassifierPerformance.objects.filter(job=self.job).order_by('-id')
        cp = cp[0]

        metrics_to_check = (
            'TPM',
            'TNM',
            'AUC',
        )

        for metric in metrics_to_check:
            self.assertIn(metric, cp.value)
