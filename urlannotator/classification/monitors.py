import sys
import os
import time
import json

FILE_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.join(FILE_DIR, '..', '..')

sys.path.append(ROOT_DIR)

from urlannotator.classification.models import Classifier
from urlannotator.classification.factories import classifier_factory

# Number of seconds between each classifier training check
TIME_INTERVAL = 1 * 60


class GoogleTrainingMonitor(object):
    """
        Periodically checks GooglePredictionClassifier instances for training
        status update.
    """
    def run(self, *args, **kwargs):
        while True:
            classifiers = Classifier.objects.filter(
                type='GooglePredictionClassifier'
            )
            for classifier_entry in classifiers:
                job = classifier_entry.job
                classifier = classifier_factory.create_classifier(
                    job_id=job.id
                )

                params = json.loads(classifier_entry.parameters)
                if 'training' in params:
                    status = classifier.get_train_status()
                    if status is not 'DONE':
                        continue
                    params.pop('training')
                    classifier_entry.parameters = json.dumps(params)
                    classifier_entry.save()
                    if not job.is_classifier_trained():
                        job.set_classifier_trained()

            time.sleep(TIME_INTERVAL)

GoogleTrainingMonitor().run()
