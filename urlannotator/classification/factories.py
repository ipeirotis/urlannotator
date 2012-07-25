import json

from urlannotator.classification.models import Classifier
from urlannotator.main.models import Job
from urlannotator.classification.classifiers import (SimpleClassifier,
    GooglePredictionClassifier)


class ClassifierFactory(object):
    def __init__(self, *args, **kwargs):
        # Cache of classifiers tied to jobs. One classifier per job,
        # cannot change.
        self.cache = {}

    def initialize_classifier(self, job_id, classifier_name):
        """
            Manages initialization of NEW classifier.
        """
        job = Job.objects.get(id=job_id)
        classifier_entry = Classifier.objects.get(job=job)

        # Custom parameters setup goes here.
        if classifier_name == 'SimpleClassifier':
            classifier_entry.type = classifier_name
            classifier_entry.parameters = ''
        elif classifier_name == 'GooglePredictionClassifier':
            classifier_entry.type = classifier_name
            params = {'model': 'job-%d' % job_id, 'training': 'RUNNING'}
            classifier_entry.parameters = json.dumps(params)
            # TODO: Training status check (separate process?) + csv data upload
            #       and model training request
            # send_event('EventNewGoogleClassiferCreated', job_id)
        classifier_entry.save()

    def create_classifier(self, job_id):
        classifier = self.cache.get(str(job_id), None)

        # Custom classifier initialization
        if not classifier:
            job = Job.objects.get(id=job_id)
            classifier_entry = Classifier.objects.get(job=job)

            if classifier_entry.type == 'SimpleClassifier':
                classifier = SimpleClassifier(job.description, ['Yes', 'No'])
            elif classifier_entry.type == 'GooglePredictionClassifier':
                classifier = GooglePredictionClassifier(job.description,
                    ['Yes', 'No'])
                params = json.loads(classifier_entry.parameters)
                classifier.model = params['model']

            # Cache newly created classifier
            self.cache[str(job_id)] = classifier

        return classifier

classifier_factory = ClassifierFactory()
