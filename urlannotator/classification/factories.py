from urlannotator.classification.models import Classifier
from urlannotator.main.models import Job
from urlannotator.classification.classifiers import SimpleClassifier


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

        classifier_entry.save()

    def create_classifier(self, job_id):
        classifier = self.cache.get(str(job_id), None)

        # Custom classifier initialization
        if not classifier:
            job = Job.objects.get(id=job_id)
            classifier_type = Classifier.objects.get(job=job).type

            if classifier_type == 'SimpleClassifier':
                classifier = SimpleClassifier(job.description, ['Yes', 'No'])

            # Cache newly created classifier
            self.cache[str(job_id)] = classifier

        return classifier

classifier_factory = ClassifierFactory()
