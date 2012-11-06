import datetime

from django.test import TestCase
from django.contrib.auth.models import User

from urlannotator.main.models import (Job, SpentStatistics, URLStatistics,
    ProgressStatistics, LABEL_YES, LABEL_NO, VotesStatistics)
from urlannotator.statistics.monitor_tasks import (spent_monitor, url_monitor,
    progress_monitor, votes_monitor)
from urlannotator.statistics.stat_extraction import (extract_progress_stats,
    extract_url_stats, extract_spent_stats, extract_performance_stats,
    update_classifier_stats, extract_votes_stats)
from urlannotator.classification.factories import classifier_factory
from urlannotator.classification.models import ClassifierPerformance
from urlannotator.flow_control.test import ToolsMockedMixin


class testJobMonitors(ToolsMockedMixin, TestCase):

    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')

        self.job = Job.objects.create_active(
            account=self.u.get_profile(),
            no_of_urls=30,
            gold_samples=[
                {'url':'google.com', 'label':LABEL_YES},
                {'url':'wikipedia.org', 'label':LABEL_YES},
                {'url':'http://www.dec.ny.gov/animals/9358.html', 'label':LABEL_YES},
                {'url':'http://www.enchantedlearning.com/subjects/mammals/raccoon/Raccoonprintout.shtml', 'label':LABEL_YES},
            ]
        )

    def testMonitors(self):
        monitor_list = [
            (SpentStatistics, spent_monitor),
            (URLStatistics, url_monitor),
            (ProgressStatistics, progress_monitor),
            (VotesStatistics, votes_monitor)
        ]
        for cls, mon in monitor_list:
            self.assertEqual(cls.objects.filter(job=self.job).count(), 1)
            mon.delay(interval=datetime.timedelta(seconds=0))
            self.assertEqual(cls.objects.filter(job=self.job).count(), 2)


class testStatExtraction(ToolsMockedMixin, TestCase):

    def setUp(self):
        self.u = User.objects.create_user(username='testing', password='test')

        self.job = Job.objects.create_active(
            account=self.u.get_profile(),
            no_of_urls=30,
            gold_samples=[
                {'url':'google.com', 'label':LABEL_YES},
                {'url':'wikipedia.org', 'label':LABEL_YES},
                {'url':'http://www.dec.ny.gov/animals/9358.html', 'label':LABEL_YES},
                {'url':'http://www.enchantedlearning.com/subjects/mammals/raccoon/Raccoonprintout.shtml', 'label':LABEL_YES},
            ]
        )
        self.job.activate()
        self.job.set_classifier_trained()

    def testExtraction(self):
        context = {}
        extractors = [
            (extract_performance_stats, 'performance_TPR'),
            (extract_performance_stats, 'performance_TNR'),
            (extract_performance_stats, 'performance_AUC'),
            (extract_spent_stats, 'spent_stats'),
            (extract_url_stats, 'url_stats'),
            (extract_progress_stats, 'progress_stats'),
            (extract_votes_stats, 'votes_stats'),
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
                    LABEL_YES: {
                        LABEL_YES: 5.0,
                        LABEL_NO: 3.0,
                    },
                    LABEL_NO: {
                        LABEL_YES: 2.0,
                        LABEL_NO: 7.0,
                    }
                }
            }
        }

        classifier.analyze = new_analyze
        update_classifier_stats(classifier, self.job)

        # 1 is initial entry, 1 is from SimpleClassifier train on create,
        # 1 is from update_classifier_stats above
        self.assertEqual(ClassifierPerformance.objects.count(), 3)
        cp = ClassifierPerformance.objects.filter(job=self.job).order_by('-id')
        cp = cp[0]

        metrics_to_check = (
            'TPR',
            'TNR',
            'AUC',
        )

        for metric in metrics_to_check:
            self.assertIn(metric, cp.value)
