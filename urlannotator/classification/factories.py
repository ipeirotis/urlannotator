import json

from urlannotator.classification.models import Classifier, TrainingSet
from urlannotator.main.models import Job
from urlannotator.classification.classifiers import (SimpleClassifier,
    GooglePredictionClassifier)


def InvalidClassifier(name, **kwargs):
    print 'Unhandled classifier', name


def SimpleClassifier_init(entry, **kwargs):
    entry.type = 'SimpleClassifier'
    params = {
        'training_set': 0,
    }
    entry.parameters = json.dumps(params)


def GooglePredictionClassifier_init(entry, prefix, job, **kwargs):
    entry.type = 'GooglePredictionClassifier'
    params = {
        'model': '%sjob-%d' % (prefix, job.id),
        'training': 'RUNNING',
        'training_set': 0,
    }
    entry.parameters = json.dumps(params)

# Contains mapping Classifier_name -> initialization_function.
classifier_inits = {
    'SimpleClassifier': SimpleClassifier_init,
    'GooglePredictionClassifier': GooglePredictionClassifier_init,
}


def SimpleClassifer_ctor(job, entry, **kwargs):
    classifier = SimpleClassifier(job.description, ['Yes', 'No'])
    classifier.id = entry.id
    training_set = TrainingSet.objects.newest_for_job(job)
    samples = training_set.training_samples.all()
    classifier.train(samples)
    return classifier


def GooglePredictionClassifer_ctor(job, entry, **kwargs):
    classifier = GooglePredictionClassifier(
        job.description,
        ['Yes', 'No'],
    )
    params = entry.parameters
    classifier.model = params['model']
    classifier.id = entry.id
    return classifier

# Contains mapping Classifier_name -> constructor_function.
classifier_ctors = {
    'SimpleClassifier': SimpleClassifer_ctor,
    'GooglePredictionClassifier': GooglePredictionClassifer_ctor,
}


class ClassifierFactory(object):
    def initialize_classifier(self, job_id, classifier_name, main=True,
        prefix=''):
        """
            Manages initialization of a NEW classifier.
        """
        job = Job.objects.get(id=job_id)
        classifier_entry = Classifier(job=job, main=main)

        fun = classifier_inits.get(classifier_name, InvalidClassifier)
        fun(
            entry=classifier_entry,
            prefix=prefix,
            job=job,
        )

        classifier_entry.save()

        if main:
            job.set_classifier_created()
        return classifier_entry.id

    def create_classifier(self, job_id):
        '''
            Creates a classifier object from a main classifier tied to the job.
        '''
        # Custom classifier initialization
        job = Job.objects.get(id=job_id)
        classifier_entry = Classifier.objects.get(job=job, main=True)

        ctor = classifier_ctors.get(classifier_entry.type, InvalidClassifier)
        classifier = ctor(
            job=job,
            entry=classifier_entry,
            name=classifier_entry.type,
        )
        return classifier

    def create_classifier_from_id(self, class_id):
        '''
            Creates a classifier object from an entry with given id.
        '''
        entry = Classifier.objects.get(id=class_id)
        ctor = classifier_ctors.get(entry.type, InvalidClassifier)
        classifier = ctor(
            job=entry.job,
            entry=entry,
            name=entry.type,
        )
        return classifier

classifier_factory = ClassifierFactory()
