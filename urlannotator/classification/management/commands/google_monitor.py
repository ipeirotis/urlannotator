import time
import json

from django.core.management.base import NoArgsCommand

from urlannotator.classification.models import Classifier
from urlannotator.classification.factories import classifier_factory
from urlannotator.statistics.stat_extraction import update_classifier_stats

# Number of seconds between each classifier training check
TIME_INTERVAL = 1 * 60


class GoogleTrainingMonitor(object):
    """
        Checks GooglePredictionClassifier instances for training
        status update.
    """
    def run(self, *args, **kwargs):
        classifiers = Classifier.objects.filter(
            type='GooglePredictionClassifier'
        )
        for classifier_entry in classifiers:
            job = classifier_entry.job
            classifier = classifier_factory.create_classifier(
                job_id=job.id
            )

            params = classifier_entry.parameters
            if 'training' in params:
                status = classifier.get_train_status()
                if not status == 'DONE':
                    continue
                params.pop('training')
                classifier_entry.parameters = json.dumps(params)
                classifier_entry.save()

                update_classifier_stats(classifier, job)

                if not job.is_classifier_trained():
                    job.set_classifier_trained()


class Command(NoArgsCommand):
    args = 'None'
    help = ('Monitors training status of Google Prediction'
        'classifiers every %d s.') % TIME_INTERVAL

    def handle(self, *args, **kwargs):
        monitor = GoogleTrainingMonitor()
        while True:
            monitor.run()
            time.sleep(TIME_INTERVAL)
